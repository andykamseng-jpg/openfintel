# engine/mapper.py

def classify_category(cat: str):
    """
    Generic financial classification (industry-agnostic)
    """

    cat = (cat or "").lower()

    # -------------------------
    # REVENUE
    # -------------------------
    if any(k in cat for k in [
        "sales", "revenue", "income", "service", "fee"
    ]):
        return "revenue"

    # -------------------------
    # VARIABLE COST (COGS)
    # -------------------------
    elif any(k in cat for k in [
        "cost", "cogs", "inventory", "purchase", "material", "supply"
    ]):
        return "variable_cost"

    # -------------------------
    # FIXED COST (OPEX)
    # -------------------------
    elif any(k in cat for k in [
        "rent", "salary", "wage", "staff", "utility",
        "subscription", "software", "insurance"
    ]):
        return "fixed_cost"

    # -------------------------
    # CASH FLOW
    # -------------------------
    elif any(k in cat for k in [
        "payment", "collection", "pos", "bank"
    ]):
        return "cash"

    return "other"


def map_db_to_engine(rows):
    revenue_total = 0
    transaction_count = 0

    variable_costs = 0
    fixed_costs = 0

    pos = 0
    supplier_payments = 0

    for r in rows:
        cat = r["category"]
        amt = float(r["amount"] or 0)

        cls = classify_category(cat)

        # -------------------------
        # REVENUE
        # -------------------------
        if cls == "revenue":
            revenue_total += amt
            transaction_count += 1
            pos += amt

        # -------------------------
        # VARIABLE COST
        # -------------------------
        elif cls == "variable_cost":
            variable_costs += abs(amt)
            supplier_payments += abs(amt)

        # -------------------------
        # FIXED COST
        # -------------------------
        elif cls == "fixed_cost":
            fixed_costs += abs(amt)

        # -------------------------
        # CASH
        # -------------------------
        elif cls == "cash":
            if amt > 0:
                pos += amt
            else:
                supplier_payments += abs(amt)

    # -------------------------
    # DERIVED (GENERIC)
    # -------------------------
    units = transaction_count if transaction_count else 1
    price = revenue_total / units if units else 0

    return {
        "units": units,
        "price": price,
        "variable_costs": variable_costs,
        "fixed_costs": fixed_costs,
        "pos": pos,
        "supplier_payments": supplier_payments,
    }