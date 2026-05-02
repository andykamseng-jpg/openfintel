from __future__ import annotations

from typing import Any

from sqlalchemy import text

from services.financial_engine import run_financial_engine


def _fetch_rows(conn, table_name: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    ]


def calculate_kpis(conn) -> dict[str, float | None]:
    result = run_financial_engine(
        balance_sheet_rows=_fetch_rows(conn, "balance_sheet"),
        cash_flow_rows=_fetch_rows(conn, "cash_flow"),
        income_statement_rows=_fetch_rows(conn, "income_statement"),
        general_ledger_rows=_fetch_rows(conn, "general_ledger"),
    )
    return result["kpis"]
