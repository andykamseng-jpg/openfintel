from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any


KPI_DEFAULTS = {
    "cashPosition": None,
    "liquidityRatio": None,
    "debtRatio": None,
    "assetEfficiency": None,
    "burnRate": None,
    "workingCapital": None,
}

OPERATING_REVENUE_TERMS = (
    "revenue",
    "sales",
    "turnover",
    "service fees",
    "service revenue",
)
NON_OPERATING_REVENUE_TERMS = (
    "other income",
    "interest income",
    "dividend income",
    "gain",
    "gains",
)
REVENUE_ADJUSTMENT_TERMS = (
    "refund",
    "refunds",
    "discount",
    "discounts",
    "return",
    "returns",
    "correction",
    "corrections",
    "accrual",
    "accruals",
    "deferral",
    "deferrals",
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
)
COGS_TERMS = (
    "cogs",
    "cost of goods",
    "cost of sales",
    "cost of revenue",
    "direct cost",
    "direct costs",
)
OPERATING_EXPENSE_TERMS = (
    "expense",
    "expenses",
    "wages",
    "salary",
    "rent",
    "utilities",
    "insurance",
    "marketing",
    "admin",
    "depreciation",
    "amortisation",
    "amortization",
)
EXPENSE_ADJUSTMENT_TERMS = (
    "adjustment",
    "adjustments",
    "correction",
    "corrections",
    "accrual",
    "accruals",
    "prepayment",
    "prepayments",
    "reversal",
    "reversals",
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


@dataclass(frozen=True)
class ReportingPeriod:
    start: date | None
    end: date | None


@dataclass(frozen=True)
class RevenueResult:
    operating: float | None
    non_operating: float | None
    adjustments: float

    @property
    def total(self) -> float | None:
        values = [value for value in (self.operating, self.non_operating) if value is not None]
        if not values and self.adjustments == 0:
            return None
        return sum(values) + self.adjustments


@dataclass(frozen=True)
class ExpenseResult:
    cogs: float | None
    operating_expenses: float | None
    adjustments: float


def amount(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def abs_amount(value: Any) -> float:
    return abs(amount(value))


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def row_text(row: dict[str, Any]) -> str:
    return " ".join(
        norm(row.get(key))
        for key in ("line_item", "category", "account", "description", "cash_flow_type")
    )


def contains(text: Any, terms: tuple[str, ...]) -> bool:
    value = norm(text)
    return any(term in value for term in terms)


def row_contains(row: dict[str, Any], terms: tuple[str, ...]) -> bool:
    value = row_text(row)
    return any(term in value for term in terms)


def section_matches(value: Any, section: str) -> bool:
    normalized = norm(value).replace("-", "_").replace(" ", "_")
    return normalized == section


def row_period(row: dict[str, Any]) -> date | None:
    period = row.get("period") or row.get("transaction_date") or row.get("as_of_date")
    return period if isinstance(period, date) else None


def dedupe_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen = set()
    output = []

    for row in rows:
        fingerprint = row.get("fingerprint")
        if fingerprint:
            dedupe_key = ("fingerprint", fingerprint)
        else:
            dedupe_key = tuple(row.get(key) for key in keys)

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        output.append(row)

    return output


def latest_balance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated_rows = [row for row in rows if row.get("as_of_date") is not None]
    if not dated_rows:
        return rows

    latest_date = max(row["as_of_date"] for row in dated_rows)
    return [row for row in rows if row.get("as_of_date") == latest_date]


def infer_reporting_period(balance_rows: list[dict[str, Any]], dated_rows: list[dict[str, Any]]) -> ReportingPeriod:
    balance_dates = [row["as_of_date"] for row in balance_rows if row.get("as_of_date") is not None]
    if balance_dates:
        end = max(balance_dates)
        return ReportingPeriod(date(end.year, 1, 1), end)

    periods = [row_period(row) for row in dated_rows]
    periods = [period for period in periods if period is not None]
    if not periods:
        return ReportingPeriod(None, None)

    end = max(periods)
    return ReportingPeriod(date(end.year, 1, 1), end)


def period_filter(rows: list[dict[str, Any]], period: ReportingPeriod) -> list[dict[str, Any]]:
    if period.start is None or period.end is None:
        return rows

    filtered = []
    undated = []

    for row in rows:
        current = row_period(row)
        if current is None:
            undated.append(row)
        elif period.start <= current <= period.end:
            filtered.append(row)

    return filtered if filtered else undated


def total_line(rows: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    for row in rows:
        if contains(row.get("line_item"), terms):
            return abs_amount(row.get("amount"))
    return None


def section_total(rows: list[dict[str, Any]], section: str) -> float | None:
    values = [
        abs_amount(row.get("amount"))
        for row in rows
        if section_matches(row.get("section"), section)
        and "total" not in norm(row.get("line_item"))
    ]
    return sum(values) if values else None


def balance_value(rows: list[dict[str, Any]], section: str, total_terms: tuple[str, ...]) -> float | None:
    section_value = section_total(rows, section)
    if section_value is not None:
        return section_value
    return total_line(rows, total_terms)


def classify_revenue(row: dict[str, Any]) -> str | None:
    if row_contains(row, REVENUE_EXCLUDED_TERMS):
        return None
    if row_contains(row, REVENUE_ADJUSTMENT_TERMS):
        return "adjustment"
    if row_contains(row, NON_OPERATING_REVENUE_TERMS):
        return "non_operating"
    if row_contains(row, OPERATING_REVENUE_TERMS):
        return "operating"
    return None


def revenue_adjustment(row: dict[str, Any]) -> float:
    value = abs_amount(row.get("amount"))
    text = row_text(row)

    if any(term in text for term in ("refund", "discount", "return", "deferral")):
        return -value
    if any(term in text for term in ("accrual",)):
        return value
    return amount(row.get("amount"))


def calculate_revenue(income_rows: list[dict[str, Any]], ledger_rows: list[dict[str, Any]]) -> RevenueResult:
    source_rows = income_rows
    if not any(classify_revenue(row) in {"operating", "non_operating"} for row in source_rows):
        source_rows = ledger_rows

    operating = []
    non_operating = []
    adjustments = 0.0

    for row in source_rows:
        classification = classify_revenue(row)
        if classification == "operating":
            operating.append(abs_amount(row.get("amount")))
        elif classification == "non_operating":
            non_operating.append(abs_amount(row.get("amount")))
        elif classification == "adjustment":
            adjustments += revenue_adjustment(row)

    return RevenueResult(
        sum(operating) if operating else None,
        sum(non_operating) if non_operating else None,
        adjustments,
    )


def classify_expense(row: dict[str, Any]) -> str | None:
    if row_contains(row, EXPENSE_ADJUSTMENT_TERMS):
        return "adjustment"
    if row_contains(row, COGS_TERMS):
        return "cogs"
    if row_contains(row, OPERATING_EXPENSE_TERMS):
        return "operating_expense"
    return None


def expense_adjustment(row: dict[str, Any]) -> float:
    text = row_text(row)
    value = abs_amount(row.get("amount"))

    if any(term in text for term in ("prepayment", "reversal")):
        return -value
    if any(term in text for term in ("accrual",)):
        return value
    return amount(row.get("amount"))


def calculate_expenses(income_rows: list[dict[str, Any]], ledger_rows: list[dict[str, Any]]) -> ExpenseResult:
    source_rows = income_rows if income_rows else ledger_rows
    cogs = []
    operating_expenses = []
    adjustments = 0.0

    for row in source_rows:
        classification = classify_expense(row)
        if classification == "cogs":
            cogs.append(abs_amount(row.get("amount")))
        elif classification == "operating_expense":
            operating_expenses.append(abs_amount(row.get("amount")))
        elif classification == "adjustment":
            adjustments += expense_adjustment(row)

    return ExpenseResult(
        sum(cogs) if cogs else None,
        sum(operating_expenses) if operating_expenses else None,
        adjustments,
    )


def cash_position(cash_flow_rows: list[dict[str, Any]], balance_rows: list[dict[str, Any]]) -> float | None:
    dated_rows = [row for row in cash_flow_rows if row.get("period") is not None]
    latest_rows = cash_flow_rows
    if dated_rows:
        latest_period = max(row["period"] for row in dated_rows)
        latest_rows = [row for row in cash_flow_rows if row.get("period") == latest_period]

    closing = total_line(
        latest_rows,
        ("closing balance", "closing cash", "cash closing", "ending cash"),
    )
    if closing is not None:
        return closing

    for row in balance_rows:
        if contains(row.get("line_item"), ("cash at bank", "cash and cash equivalents", "cash")):
            return abs_amount(row.get("amount"))
    return None


def burn_rate(cash_flow_rows: list[dict[str, Any]]) -> float | None:
    monthly = defaultdict(float)

    for row in cash_flow_rows:
        current = row_period(row)
        if current is None or row_contains(row, BALANCE_POSITION_TERMS):
            continue
        monthly[current.strftime("%Y-%m")] += amount(row.get("amount"))

    negative_months = [abs(total) for total in monthly.values() if total < 0]
    if not negative_months:
        return None
    return sum(negative_months) / len(negative_months)


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return abs(numerator) / abs(denominator)


def run_financial_engine(
    balance_sheet_rows: list[dict[str, Any]],
    cash_flow_rows: list[dict[str, Any]],
    income_statement_rows: list[dict[str, Any]],
    general_ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    validated_balance = latest_balance_rows(dedupe_rows(
        balance_sheet_rows,
        ("as_of_date", "line_item", "section", "amount"),
    ))
    validated_cash_flow = dedupe_rows(
        cash_flow_rows,
        ("period", "line_item", "cash_flow_type", "amount"),
    )
    validated_income = dedupe_rows(
        income_statement_rows,
        ("period", "line_item", "category", "amount"),
    )
    validated_ledger = dedupe_rows(
        general_ledger_rows,
        ("transaction_date", "description", "account", "category", "amount"),
    )

    reporting_period = infer_reporting_period(
        validated_balance,
        validated_income + validated_cash_flow + validated_ledger,
    )
    filtered_cash_flow = period_filter(validated_cash_flow, reporting_period)
    filtered_income = period_filter(validated_income, reporting_period)
    filtered_ledger = period_filter(validated_ledger, reporting_period)

    revenue = calculate_revenue(filtered_income, filtered_ledger)
    expenses = calculate_expenses(filtered_income, filtered_ledger)

    current_assets = balance_value(
        validated_balance,
        "current_assets",
        ("total current assets", "current assets"),
    )
    current_liabilities = balance_value(
        validated_balance,
        "current_liabilities",
        ("total current liabilities", "current liabilities"),
    )
    non_current_liabilities = balance_value(
        validated_balance,
        "non_current_liabilities",
        ("total non-current liabilities", "non-current liabilities", "non current liabilities"),
    )
    total_assets = balance_value(validated_balance, "assets", ("total assets",))
    if total_assets is None:
        current_asset_total = balance_value(
            validated_balance,
            "current_assets",
            ("total current assets", "current assets"),
        ) or 0
        non_current_asset_total = balance_value(
            validated_balance,
            "non_current_assets",
            ("total non-current assets", "non-current assets", "non current assets"),
        ) or 0
        total_assets = current_asset_total + non_current_asset_total or None

    total_liabilities = total_line(validated_balance, ("total liabilities",))
    if total_liabilities is None:
        total_liabilities = (current_liabilities or 0) + (non_current_liabilities or 0)
        total_liabilities = total_liabilities or None

    working_capital = (
        current_assets - abs(current_liabilities)
        if current_assets is not None and current_liabilities is not None
        else None
    )

    kpis = {
        **KPI_DEFAULTS,
        "cashPosition": cash_position(filtered_cash_flow, validated_balance),
        "liquidityRatio": ratio(current_assets, current_liabilities),
        "debtRatio": ratio(total_liabilities, total_assets),
        "assetEfficiency": ratio(revenue.total, total_assets),
        "burnRate": burn_rate(filtered_cash_flow),
        "workingCapital": working_capital,
    }

    return {
        "period": reporting_period,
        "revenue": revenue,
        "expenses": expenses,
        "kpis": kpis,
    }
