from sqlalchemy import text

# -------------------------
# CATEGORY MAPPING (STEP 1)
# -------------------------
CATEGORY_MAP = {
    # COGS
    "cost of goods": "cogs",
    "cogs": "cogs",
    "materials": "cogs",
    "inventory": "cogs",
    "direct cost": "cogs",
    "cost of sales": "cogs",
    "production": "cogs",
    "manufacturing": "cogs",

    # OPEX
    "rent": "opex",
    "salary": "opex",
    "wages": "opex",
    "utilities": "opex",
    "insurance": "opex",
    "marketing": "opex",
    "advertising": "opex",
    "software": "opex",
}
def classify_category(line_item: str) -> str:
    text = (line_item or "").lower()

    for keyword, category in CATEGORY_MAP.items():
        if keyword in text:
            return category

    return "opex"  # safe fallback
def calculate_kpis(conn):

    # -------------------------
    # CURRENT ASSETS
    # -------------------------
    current_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section = 'current_assets'
    """)).scalar()

    # -------------------------
    # NON-CURRENT ASSETS
    # -------------------------
    non_current_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%non-current%'
    """)).scalar()

    # -------------------------
    # TOTAL ASSETS
    # -------------------------
    total_assets = current_assets + non_current_assets

    # -------------------------
    # CURRENT LIABILITIES
    # -------------------------
    current_liabilities = conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%current liabil%'
    """)).scalar()

    # -------------------------
    # TOTAL LIABILITIES
    # -------------------------
    total_liabilities = conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%liabil%'
    """)).scalar()

    # -------------------------
    # CASH POSITION
    # -------------------------
    cash = current_assets

    # -------------------------
    # REVENUE
    # -------------------------
    revenue = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE amount > 0
    """)).scalar()

       # -------------------------
    # -------------------------
    # CLASSIFY EXPENSES (STEP 1)
    # -------------------------
    rows = conn.execute(text("""
        SELECT line_item, amount
        FROM income_statement
        WHERE amount < 0
    """)).fetchall()

    cogs = 0
    operating_expenses = 0

    for row in rows:
        line_item = str(row[0] or "")
        amount = abs(float(row[1] or 0))

        category = classify_category(line_item)

        if category == "cogs":
            cogs += amount
        else:
            operating_expenses += amount

    expenses = cogs + operating_expenses

    # -------------------------
    # NET PROFIT
    # -------------------------
    net_profit = revenue - expenses

    # -------------------------
    # BURN RATE (deduplicated monthly outflow)
    # -------------------------
    burn_rate = conn.execute(
        text("""
            SELECT COALESCE(AVG(monthly_outflow), 0)
            FROM (
                SELECT DATE_TRUNC('month', period) as m,
                       MAX(ABS(amount)) as monthly_outflow
                FROM cash_flow
                WHERE LOWER(cash_flow_type) = 'operating outflow'
                GROUP BY m
            ) t
        """)
    ).scalar()
    # -------------------------
    # FINAL CALCULATIONS
    # -------------------------
    liquidity_ratio = (current_assets / current_liabilities) if current_liabilities else 0
    debt_ratio = (total_liabilities / total_assets) if total_assets else 0
    asset_efficiency = (revenue / total_assets) if total_assets else 0
    working_capital = current_assets - current_liabilities
    net_profit = revenue - expenses

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