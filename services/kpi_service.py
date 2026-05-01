from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text


KPI_DEFAULTS = {
    "cashPosition": None,
    "liquidityRatio": None,
    "debtRatio": None,
    "assetEfficiency": None,
    "burnRate": None,
    "workingCapital": None,
}


def _amount(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(value: Any, terms: tuple[str, ...]) -> bool:
    text_value = _norm(value)
    return any(term in text_value for term in terms)


def _fetch_rows(conn, table_name: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    ]


def _latest_balance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated_rows = [row for row in rows if row.get("as_of_date") is not None]
    if not dated_rows:
        return rows

    latest_date = max(row["as_of_date"] for row in dated_rows)
    return [row for row in rows if row.get("as_of_date") == latest_date]


def _latest_cash_flow_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated_rows = [row for row in rows if row.get("period") is not None]
    if not dated_rows:
        return rows

    latest_period = max(row["period"] for row in dated_rows)
    return [row for row in rows if row.get("period") == latest_period]


def _line_value(rows: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    for row in rows:
        if _contains(row.get("line_item"), terms):
            return _amount(row.get("amount"))
    return None


def _section_sum(rows: list[dict[str, Any]], section: str) -> float:
    return sum(_amount(row.get("amount")) for row in rows if _norm(row.get("section")) == section)


def _income_revenue(rows: list[dict[str, Any]]) -> float:
    revenue_terms = ("revenue", "sales", "income")
    total = sum(
        _amount(row.get("amount"))
        for row in rows
        if _contains(row.get("line_item"), revenue_terms)
        or _contains(row.get("category"), revenue_terms)
    )
    if total:
        return total

    positives = [_amount(row.get("amount")) for row in rows if _amount(row.get("amount")) > 0]
    return sum(positives)


def _average_negative_cash_flow(rows: list[dict[str, Any]]) -> float | None:
    monthly = defaultdict(float)

    for row in rows:
        period = row.get("period")
        key = period.strftime("%Y-%m") if hasattr(period, "strftime") else str(period or "unknown")
        monthly[key] += _amount(row.get("amount"))

    negative_months = [abs(total) for total in monthly.values() if total < 0]
    if not negative_months:
        return None

    return sum(negative_months) / len(negative_months)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def calculate_kpis(conn) -> dict[str, float | None]:
    balance_rows = _latest_balance_rows(_fetch_rows(conn, "balance_sheet"))
    cash_flow_rows = _fetch_rows(conn, "cash_flow")
    latest_cash_rows = _latest_cash_flow_rows(cash_flow_rows)
    income_rows = _fetch_rows(conn, "income_statement")

    cash_position = _line_value(
        latest_cash_rows,
        ("closing balance", "closing cash", "cash closing", "ending cash"),
    )
    if cash_position is None:
        cash_position = _line_value(balance_rows, ("cash at bank", "cash and cash equivalents", "cash"))

    current_assets = _line_value(balance_rows, ("total current assets", "current assets"))
    if current_assets is None:
        current_assets = _section_sum(balance_rows, "current_assets") or None

    current_liabilities = _line_value(
        balance_rows,
        ("total current liabilities", "current liabilities"),
    )
    if current_liabilities is None:
        current_liabilities = _section_sum(balance_rows, "current_liabilities") or None

    total_assets = _line_value(balance_rows, ("total assets",))
    if total_assets is None:
        total_assets = (
            _section_sum(balance_rows, "current_assets")
            + _section_sum(balance_rows, "non_current_assets")
        ) or None

    total_liabilities = _line_value(balance_rows, ("total liabilities",))
    if total_liabilities is None:
        total_liabilities = (
            _section_sum(balance_rows, "current_liabilities")
            + _section_sum(balance_rows, "non_current_liabilities")
        ) or None

    revenue = _income_revenue(income_rows)
    working_capital = (
        current_assets - current_liabilities
        if current_assets is not None and current_liabilities is not None
        else None
    )

    return {
        **KPI_DEFAULTS,
        "cashPosition": cash_position,
        "liquidityRatio": _ratio(current_assets, current_liabilities),
        "debtRatio": _ratio(total_liabilities, total_assets),
        "assetEfficiency": _ratio(revenue, total_assets),
        "burnRate": _average_negative_cash_flow(cash_flow_rows),
        "workingCapital": working_capital,
    }
