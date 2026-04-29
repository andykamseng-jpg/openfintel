def calc_revenue(units, price):
    return units * price

def calc_cogs(variable_costs):
    return variable_costs

def calc_gross_margin(revenue, cogs):
    return revenue - cogs

def calc_operating_expenses(fixed_costs):
    return fixed_costs

def calc_net_profit(gross_margin, operating_expenses):
    return gross_margin - operating_expenses

def calc_cash_flow(net_profit, pos, supplier_payments):
    return net_profit + pos - supplier_payments