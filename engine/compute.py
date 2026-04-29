from .nodes import normalize_inputs
from .formulas import *

def compute_kpis(raw_data):
    data = normalize_inputs(raw_data)

    revenue = calc_revenue(data["units"], data["price"])
    cogs = calc_cogs(data["variable_costs"])
    gross_margin = calc_gross_margin(revenue, cogs)

    operating_expenses = calc_operating_expenses(data["fixed_costs"])
    net_profit = calc_net_profit(gross_margin, operating_expenses)

    cash_flow = calc_cash_flow(
        net_profit,
        data["pos"],
        data["supplier_payments"]
    )

    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "operating_expenses": operating_expenses,
        "net_profit": net_profit,
        "cash_flow": cash_flow,
    }