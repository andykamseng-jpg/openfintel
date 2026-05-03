from sqlalchemy import text

# -------------------------
# CATEGORY MAPPING (fallback if DB empty)
# -------------------------
CATEGORY_MAP = {
    "cost of goods": "cogs",
    "cogs": "cogs",
    "materials": "cogs",
    "inventory": "cogs",
    "direct cost": "cogs",
    "cost of sales": "cogs",
    "production": "cogs",
    "manufacturing": "cogs",

    "rent": "opex",
    "salary": "opex",
    "wages": "opex",
    "utilities": "opex",
    "insurance": "opex",
    "marketing": "opex",
    "advertising": "opex",
    "software": "opex",
}


def classify_category_db(conn, line_item: str) -> str:
    text_val = (line_item or "").lower()

    rows = conn.execute(text("""
        SELECT keyword, category FROM category_mapping
    """)).fetchall()

    for keyword, category in rows:
        if keyword and keyword.lower() in text_val:
            return category

    # fallback
    for keyword, category in CATEGORY_MAP.items():
        if keyword in text_val:
            return category

    return "opex"


def calculate_kpis(conn):

    # -------------------------
    # GET LATEST UPLOADS (PER TABLE)
    # -------------------------
    latest_balance_upload = conn.execute(text("""
        SELECT MAX(upload_id) FROM balance_sheet
    """)).scalar()

    latest_income_upload = conn.execute(text("""
        SELECT MAX(upload_id) FROM income_statement
    """)).scalar()

    latest_cashflow_upload = conn.execute(text("""
        SELECT MAX(upload_id) FROM cash_flow
    """)).scalar()

    if not latest_balance_upload or not latest_income_upload:
        return {}

    # -------------------------
    # TOTAL ASSETS (FIXED)
    # -------------------------
    total_assets = float(conn.execute(text("""
    SELECT COALESCE(SUM(amount),0)
    FROM balance_sheet
    WHERE section IN ('current_assets', 'non_current_assets')
    AND upload_id = :upload_id
    """), {"upload_id": latest_balance_upload}).scalar() or 0)

    # -------------------------
    # CURRENT ASSETS
    # -------------------------
    current_assets = float(conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section = 'current_assets'
        AND upload_id = :upload_id
    """), {"upload_id": latest_balance_upload}).scalar() or 0)

    # -------------------------
    # CURRENT LIABILITIES
    # -------------------------
    current_liabilities = float(conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%current liabil%'
        AND upload_id = :upload_id
    """), {"upload_id": latest_balance_upload}).scalar() or 0)

    # -------------------------
    # TOTAL LIABILITIES
    # -------------------------
    total_liabilities = float(conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%liabil%'
        AND upload_id = :upload_id
    """), {"upload_id": latest_balance_upload}).scalar() or 0)

    # -------------------------
    # CASH POSITION
    # -------------------------
    cash = current_assets

    # -------------------------
    # REVENUE
    # -------------------------
    revenue = float(conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE amount > 0
        AND upload_id = :upload_id
    """), {"upload_id": latest_income_upload}).scalar() or 0)

    # -------------------------
    # CLASSIFY EXPENSES
    # -------------------------
    rows = conn.execute(text("""
        SELECT line_item, amount
        FROM income_statement
        WHERE amount < 0
        AND upload_id = :upload_id
    """), {"upload_id": latest_income_upload}).fetchall()

    cogs = 0.0
    operating_expenses = 0.0

    for row in rows:
        line_item = str(row[0] or "")
        amount = abs(float(row[1] or 0))

        category = classify_category_db(conn, line_item)

        if category == "cogs":
            cogs += amount
        else:
            operating_expenses += amount

    expenses = cogs + operating_expenses
    net_profit = revenue - expenses

    # -------------------------
    # BURN RATE
    # -------------------------
    burn_rate = 0.0
    if latest_cashflow_upload:
        burn_rate = float(conn.execute(text("""
            SELECT COALESCE(AVG(monthly_outflow), 0)
            FROM (
                SELECT DATE_TRUNC('month', period) as m,
                       MAX(ABS(amount)) as monthly_outflow
                FROM cash_flow
                WHERE LOWER(cash_flow_type) = 'operating outflow'
                AND upload_id = :upload_id
                GROUP BY m
            ) t
        """), {"upload_id": latest_cashflow_upload}).scalar() or 0)

    # -------------------------
    # FINAL CALCULATIONS
    # -------------------------
    liquidity_ratio = (current_assets / current_liabilities) if current_liabilities else 0
    debt_ratio = (total_liabilities / total_assets) if total_assets else 0
    asset_efficiency = (revenue / total_assets) if total_assets else 0
    working_capital = current_assets - current_liabilities

    # -------------------------
    # RETURN
    # -------------------------
    return {
        "cash_position": cash,
        "liquidity_ratio": round(liquidity_ratio, 2),
        "debt_ratio": round(debt_ratio, 2),
        "asset_efficiency": round(asset_efficiency, 2),
        "burn_rate": burn_rate,
        "working_capital": working_capital,
        "bas": {
            "revenue": revenue,
            "cogs": -cogs,
            "operating_expenses": -operating_expenses,
            "net_profit": net_profit
        }
    }