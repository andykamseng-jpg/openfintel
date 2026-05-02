from sqlalchemy import text


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
    # EXPENSES
    # -------------------------
    expenses = conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM income_statement
        WHERE amount < 0
    """)).scalar()

       # -------------------------
    # BURN RATE (use Operating Net per month)
    # -------------------------
    burn_rate = conn.execute(text("""
        SELECT COALESCE(AVG(ABS(amount)), 0)
        FROM cash_flow
        WHERE LOWER(line_item) = 'operating net'
    """)).scalar()

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
            "cogs": 0,
            "operating_expenses": -expenses,
            "net_profit": net_profit
        }
    }