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

REVENUE_TERMS = (
    "revenue",
    "sales",
    "turnover",
    "income",
    "service fees",
    "service revenue",
)
REVENUE_EXCLUDED_TERMS = (
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
BALANCE_POSITION_TERMS = (
    "opening balance",
    "closing balance",
    "opening cash",
    "closing cash",
    "cash at beginning",
    "cash at end",
    "beginning cash",
    "ending cash",
)


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


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        _norm(row.get(key))
        for key in ("line_item", "category", "account", "description", "cash_flow_type")
    )


def _row_contains(row: dict[str, Any], terms: tuple[str, ...]) -> bool:
    text_value = _row_text(row)
    return any(term in text_value for term in terms)


def _section_matches(value: Any, section: str) -> bool:
    normalized = _norm(value).replace("-", "_").replace(" ", "_")
    return normalized == section


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


def _total_line(rows: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    for row in rows:
        if _contains(row.get("line_item"), terms):
            return _abs_amount(row.get("amount"))
    return None


def _section_total(rows: list[dict[str, Any]], section: str) -> float | None:
    values = [
        _abs_amount(row.get("amount"))
        for row in rows
        if _section_matches(row.get("section"), section)
        and "total" not in _norm(row.get("line_item"))
    ]
    return sum(values) if values else None


def _balance_value(
    rows: list[dict[str, Any]],
    section: str,
    total_terms: tuple[str, ...],
) -> float | None:
    section_value = _section_total(rows, section)
    if section_value is not None:
        return section_value
    return _total_line(rows, total_terms)


def _cash_position(cash_flow_rows: list[dict[str, Any]], balance_rows: list[dict[str, Any]]) -> float | None:
    latest_cash_rows = _latest_cash_flow_rows(cash_flow_rows)
    closing = _total_line(
        latest_cash_rows,
        ("closing balance", "closing cash", "cash closing", "ending cash"),
    )
    if closing is not None:
        return closing

    for row in balance_rows:
        if _contains(
            row.get("line_item"),
            ("cash at bank", "cash and cash equivalents", "cash"),
        ):
            return _abs_amount(row.get("amount"))
    return None


def _is_revenue_row(row: dict[str, Any]) -> bool:
    return _row_contains(row, REVENUE_TERMS) and not _row_contains(row, REVENUE_EXCLUDED_TERMS)


def _income_statement_revenue(rows: list[dict[str, Any]]) -> float | None:
    values = [_abs_amount(row.get("amount")) for row in rows if _is_revenue_row(row)]
    return sum(values) if values else None


def _ledger_revenue(rows: list[dict[str, Any]]) -> float | None:
    values = [
        _abs_amount(row.get("amount"))
        for row in rows
        if _is_revenue_row(row)
    ]
    return sum(values) if values else None


def _revenue(
    income_statement_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
) -> float | None:
    income_revenue = _income_statement_revenue(income_statement_rows)
    if income_revenue is not None:
        return income_revenue
    return _ledger_revenue(ledger_rows)


def _cash_flow_amount_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("period") is not None
        and not _row_contains(row, BALANCE_POSITION_TERMS)
    ]


def _burn_rate(rows: list[dict[str, Any]]) -> float | None:
    monthly = defaultdict(float)

    for row in _cash_flow_amount_rows(rows):
        period = row.get("period")
        key = period.strftime("%Y-%m") if hasattr(period, "strftime") else str(period)
        monthly[key] += _amount(row.get("amount"))

    negative_months = [abs(total) for total in monthly.values() if total < 0]
    if not negative_months:
        return None

    return sum(negative_months) / len(negative_months)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return abs(numerator) / abs(denominator)


def calculate_kpis(conn) -> dict[str, float | None]:
    balance_rows = _latest_balance_rows(_fetch_rows(conn, "balance_sheet"))
    cash_flow_rows = _fetch_rows(conn, "cash_flow")
    income_rows = _fetch_rows(conn, "income_statement")
    ledger_rows = _fetch_rows(conn, "general_ledger")

    current_assets = _balance_value(
        balance_rows,
        "current_assets",
        ("total current assets", "current assets"),
    )
    current_liabilities = _balance_value(
        balance_rows,
        "current_liabilities",
        ("total current liabilities", "current liabilities"),
    )
    non_current_liabilities = _balance_value(
        balance_rows,
        "non_current_liabilities",
        ("total non-current liabilities", "non-current liabilities", "non current liabilities"),
    )
    total_assets = _balance_value(
        balance_rows,
        "assets",
        ("total assets",),
    )
    if total_assets is None:
        current_asset_total = _balance_value(
            balance_rows,
            "current_assets",
            ("total current assets", "current assets"),
        ) or 0
        non_current_asset_total = _balance_value(
            balance_rows,
            "non_current_assets",
            ("total non-current assets", "non-current assets", "non current assets"),
        ) or 0
        total_assets = current_asset_total + non_current_asset_total or None

    total_liabilities = _total_line(balance_rows, ("total liabilities",))
    if total_liabilities is None:
        total_liabilities = (current_liabilities or 0) + (non_current_liabilities or 0)
        total_liabilities = total_liabilities or None

    revenue = _revenue(income_rows, ledger_rows)

    working_capital = (
        current_assets - abs(current_liabilities)
        if current_assets is not None and current_liabilities is not None
        else None
    )

    return {
        **KPI_DEFAULTS,
        "cashPosition": _cash_position(cash_flow_rows, balance_rows),
        "liquidityRatio": _ratio(current_assets, current_liabilities),
        "debtRatio": _ratio(total_liabilities, total_assets),
        "assetEfficiency": _ratio(revenue, total_assets),
        "burnRate": _burn_rate(cash_flow_rows),
        "workingCapital": working_capital,
    }
