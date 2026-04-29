from .graph import GraphEngine, multiply_parents, sum_parents


# -------------------------
# BUILD GRAPH
# -------------------------
def build_graph_from_data(raw):
    g = GraphEngine()

    # --- INPUT NODES ---
    g.add_node("units", "Units", raw.get("units", 0))
    g.add_node("price", "Price", raw.get("price", 0))

    g.add_node("variable_costs", "Variable Costs", raw.get("variable_costs", 0))
    g.add_node("fixed_costs", "Fixed Costs", raw.get("fixed_costs", 0))

    g.add_node("pos", "POS Collection", raw.get("pos", 0))
    g.add_node("supplier_payments", "Supplier Payments", raw.get("supplier_payments", 0))

    # --- DERIVED NODES ---
    g.add_node("revenue", "Revenue", calc_fn=multiply_parents)
    g.connect("units", "revenue")
    g.connect("price", "revenue")

    g.add_node("cogs", "COGS", calc_fn=sum_parents)
    g.connect("variable_costs", "cogs")

    g.add_node(
        "gross_margin",
        "Gross Margin",
        calc_fn=lambda p: p[0].value - p[1].value
    )
    g.connect("revenue", "gross_margin")
    g.connect("cogs", "gross_margin")

    g.add_node("operating_expenses", "Operating Expenses", calc_fn=sum_parents)
    g.connect("fixed_costs", "operating_expenses")

    g.add_node(
        "net_profit",
        "Net Profit",
        calc_fn=lambda p: p[0].value - p[1].value
    )
    g.connect("gross_margin", "net_profit")
    g.connect("operating_expenses", "net_profit")

    g.add_node(
        "cash_flow",
        "Cash Flow",
        calc_fn=lambda p: p[0].value + p[1].value - p[2].value
    )
    g.connect("net_profit", "cash_flow")
    g.connect("pos", "cash_flow")
    g.connect("supplier_payments", "cash_flow")

    return g


# -------------------------
# RUN ENGINE (FINAL)
# -------------------------
def run_engine(raw_data):
    g = build_graph_from_data(raw_data)

    # 🔥 SINGLE COMPUTATION SOURCE
    g.recalculate()

    # -------------------------
    # EXTRACT KPI DIRECTLY FROM GRAPH
    # -------------------------
    kpis = {
        "revenue": g.get_node("revenue").value,
        "cogs": g.get_node("cogs").value,
        "gross_margin": g.get_node("gross_margin").value,
        "operating_expenses": g.get_node("operating_expenses").value,
        "net_profit": g.get_node("net_profit").value,
        "cash_flow": g.get_node("cash_flow").value,
    }

    # -------------------------
    # GRAPH OUTPUT (FOR UI)
    # -------------------------
    graph_output = {
        node_id: node.value
        for node_id, node in g.nodes.items()
    }

    return {
        "kpis": kpis,
        "graph": graph_output
    }