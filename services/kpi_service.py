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


def _abs_amount(value: Any) -> float:
    return abs(_amount(value))


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(value: Any, terms: tuple[str, ...]) -> bool:
    text_value = _norm(value)
    return any(term in text_value for term in terms)


def _contains_any(row: dict[str, Any], terms: tuple[str, ...]) -> bool:
    return _contains(row.get("line_item"), terms) or _contains(row.get("category"), terms)


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


def _line_abs_value(rows: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    value = _line_value(rows, terms)
    return abs(value) if value is not None else None


def _section_sum(rows: list[dict[str, Any]], section: str) -> float:
    return sum(_amount(row.get("amount")) for row in rows if _norm(row.get("section")) == section)


def _section_abs_sum(rows: list[dict[str, Any]], section: str) -> float:
    return sum(_abs_amount(row.get("amount")) for row in rows if _norm(row.get("section")) == section)


def _income_revenue(rows: list[dict[str, Any]]) -> float | None:
    revenue_terms = (
        "revenue",
        "sales",
        "turnover",
        "income",
        "service fees",
        "service revenue",
    )
    excluded_terms = (
        "cost of sales",
        "cost of revenue",
        "expense",
        "expenses",
        "tax",
        "net income",
        "net profit",
        "gross profit",
        "other income",
        "interest income",
    )

    total = sum(
        _abs_amount(row.get("amount"))
        for row in rows
        if _contains_any(row, revenue_terms)
        and not _contains_any(row, excluded_terms)
    )
    if total:
        return total

    positives = [
        _amount(row.get("amount"))
        for row in rows
        if _amount(row.get("amount")) > 0
        and not _contains_any(row, excluded_terms)
    ]
    return sum(positives) if positives else None


def _average_negative_cash_flow(rows: list[dict[str, Any]]) -> float | None:
    monthly = defaultdict(float)
    net_terms = (
        "net cash flow",
        "net cash movement",
        "net increase",
        "net decrease",
        "net change in cash",
    )
    balance_terms = (
        "opening balance",
        "closing balance",
        "opening cash",
        "closing cash",
        "cash at beginning",
        "cash at end",
        "beginning cash",
        "ending cash",
    )
    net_rows = [
        row
        for row in rows
        if _contains(row.get("line_item"), net_terms)
        or _contains(row.get("cash_flow_type"), net_terms)
    ]
    source_rows = net_rows or [
        row
        for row in rows
        if not _contains(row.get("line_item"), balance_terms)
        and not _contains(row.get("cash_flow_type"), balance_terms)
    ]

    for row in source_rows:
        period = row.get("period")
        if period is None:
            continue
        key = period.strftime("%Y-%m") if hasattr(period, "strftime") else str(period or "unknown")
        monthly[key] += _amount(row.get("amount"))

    negative_months = [abs(total) for total in monthly.values() if total < 0]
    if not negative_months:
        return None

    return sum(negative_months) / len(negative_months)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return abs(numerator) / abs(denominator)


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

    current_assets = _line_abs_value(balance_rows, ("total current assets", "current assets"))
    if current_assets is None:
        current_assets = _section_abs_sum(balance_rows, "current_assets") or None

    current_liabilities = _line_abs_value(
        balance_rows,
        ("total current liabilities", "current liabilities"),
    )
    if current_liabilities is None:
        current_liabilities = _section_abs_sum(balance_rows, "current_liabilities") or None

    total_assets = _line_abs_value(balance_rows, ("total assets",))
    if total_assets is None:
        total_assets = (
            _section_abs_sum(balance_rows, "current_assets")
            + _section_abs_sum(balance_rows, "non_current_assets")
        ) or None

    total_liabilities = _line_abs_value(balance_rows, ("total liabilities",))
    if total_liabilities is None:
        total_liabilities = (
            _section_abs_sum(balance_rows, "current_liabilities")
            + _section_abs_sum(balance_rows, "non_current_liabilities")
        ) or None

    revenue = _income_revenue(income_rows)
    asset_efficiency = _ratio(revenue, total_assets) if revenue is not None else None
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
        "assetEfficiency": asset_efficiency,
        "burnRate": _average_negative_cash_flow(cash_flow_rows),
        "workingCapital": working_capital,
    }
