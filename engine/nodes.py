from typing import Dict, Any

def normalize_inputs(data: Dict[str, Any]) -> Dict[str, float]:
    return {
        "units": float(data.get("units", 0)),
        "price": float(data.get("price", 0)),

        "variable_costs": float(data.get("variable_costs", 0)),
        "fixed_costs": float(data.get("fixed_costs", 0)),

        "pos": float(data.get("pos", 0)),
        "supplier_payments": float(data.get("supplier_payments", 0)),
    }