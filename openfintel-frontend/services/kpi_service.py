def calculate_engine_result(conn):
    return {
        "summary": {
            "revenue": 0,
            "cogs": 0,
            "operating_expenses": 0,
            "net_profit": 0,
            "gross_margin": 0,
        }
    }

def calculate_kpis(conn):
    return {
        "cash_position": 0,
        "liquidity_ratio": 0,
        "debt_ratio": 0,
        "burn_rate": 0,
        "working_capital": 0,
    }