# services/kpi_service.py

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
    # 📊 CURRENT ASSETS / LIABILITIES
    # -------------------------
    current_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section = 'current_assets'
    """)).scalar()

    current_liabilities = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section = 'current_liabilities'
    """)).scalar()

    # -------------------------
    # 📉 TOTAL ASSETS / LIABILITIES
    # -------------------------
    total_assets = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section IN ('current_assets','non_current_assets')
    """)).scalar()

    total_liabilities = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM balance_sheet
        WHERE section IN ('current_liabilities','non_current_liabilities')
    """)).scalar()

    # -------------------------
    # 📈 REVENUE
    # -------------------------
    revenue = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) SIMILAR TO '%(revenue|sales|income)%'
        AND LOWER(line_item) NOT SIMILAR TO '%(cost|expense|tax)%'
    """)).scalar()

    # -------------------------
    # 📉 COGS
    # -------------------------
    cogs = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) SIMILAR TO '%(cost of sales|cogs|ingredients)%'
    """)).scalar()

    # -------------------------
    # ⚙️ OPERATING EXPENSES
    # -------------------------
    opex = conn.execute(text("""
        SELECT COALESCE(SUM(amount),0)
        FROM income_statement
        WHERE LOWER(line_item) SIMILAR TO '%(expense|wages|rent|utilities)%'
    """)).scalar()

    # -------------------------
    # 🔥 BURN RATE (CASH FLOW)
    # -------------------------
    burn_rate = conn.execute(text("""
        SELECT ABS(COALESCE(SUM(amount),0))
        FROM cash_flow
        WHERE amount < 0
    """)).scalar()

    # -------------------------
    # 📊 CALCULATIONS
    # -------------------------
    liquidity_ratio = (current_assets / current_liabilities) if current_liabilities else 0
    debt_ratio = (total_liabilities / total_assets) if total_assets else 0
    asset_efficiency = (revenue / total_assets) if total_assets else 0
    working_capital = current_assets - current_liabilities
    net_profit = revenue - cogs - opex

    # -------------------------
    # 🎯 OUTPUT (MATCH YOUR FRONTEND)
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
            "operating_expenses": -opex,
            "net_profit": net_profit
        }
    }