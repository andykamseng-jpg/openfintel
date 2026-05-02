from sqlalchemy import text


def calculate_kpis(conn):

    # -------------------------
    # 💰 CASH POSITION
    # -------------------------
    cash = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(line_item) LIKE '%cash%'
    """)).scalar()

    # -------------------------
    # 📊 CURRENT ASSETS
    # -------------------------
    current_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(section) LIKE '%current asset%'
           OR LOWER(line_item) LIKE '%cash%'
           OR LOWER(line_item) LIKE '%receivable%'
           OR LOWER(line_item) LIKE '%inventory%'
    """)).scalar()

    # -------------------------
    # 📊 CURRENT LIABILITIES
    # -------------------------
    current_liabilities = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(section) LIKE '%current liabil%'
           OR LOWER(line_item) LIKE '%payable%'
           OR LOWER(line_item) LIKE '%credit%'
    """)).scalar()

    # -------------------------
    # 📉 TOTAL ASSETS
    # -------------------------
    total_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(section) LIKE '%asset%'
    """)).scalar()

    # -------------------------
    # 📉 TOTAL LIABILITIES
    # -------------------------
    total_liabilities = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE LOWER(section) LIKE '%liabil%'
    """)).scalar()

    # -------------------------
    # 📈 REVENUE
    # -------------------------
    revenue = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) LIKE '%sales%'
           OR LOWER(line_item) LIKE '%revenue%'
    """)).scalar()

    # -------------------------
    # 📉 COGS
    # -------------------------
    cogs = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) LIKE '%cost%'
           OR LOWER(line_item) LIKE '%cogs%'
    """)).scalar()

    # -------------------------
    # ⚙️ OPERATING EXPENSES
    # -------------------------
    opex = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) LIKE '%expense%'
           OR LOWER(line_item) LIKE '%wage%'
           OR LOWER(line_item) LIKE '%rent%'
    """)).scalar()

    # -------------------------
    # 🔥 BURN RATE
    # -------------------------
    burn_rate = conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM cash_flow
        WHERE amount < 0
    """)).scalar()

    # -------------------------
    # 📊 FINAL CALCULATIONS
    # -------------------------
    liquidity_ratio = (current_assets / current_liabilities) if current_liabilities else 0
    debt_ratio = (total_liabilities / total_assets) if total_assets else 0
    asset_efficiency = (revenue / total_assets) if total_assets else 0
    working_capital = current_assets - current_liabilities
    net_profit = revenue - cogs - opex

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
            "operating_expenses": -opex,
            "net_profit": net_profit
        }
    }