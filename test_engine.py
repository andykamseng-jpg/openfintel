from engine.compute import compute_kpis

print(compute_kpis({
    "units": 200,
    "price": 15,
    "variable_costs": 2500,
    "fixed_costs": 3000,
    "pos": 3000,
    "supplier_payments": 1000
}))