
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
import os, re, unicodedata, hashlib

from engine.adapter import run_engine
from engine.mapper import map_db_to_engine
from services.kpi_service import calculate_kpis

app = FastAPI()

# -------------------------
# CORS (FIXED)
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://www.openfintel.com",
        "https://openfintel-nine.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# DATABASE
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

VALID_DOC_TYPES = {
    "general_ledger",
    "income_statement",
    "cash_flow",
    "balance_sheet",
}


def init_database():
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        for statement in schema.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))


@app.on_event("startup")
def startup():
    init_database()

# -------------------------
# CLEAN TEXT
# -------------------------
def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x)
    x = unicodedata.normalize("NFKD", x)
    x = x.encode("ascii", "ignore").decode()
    x = x.strip().lower()
    x = " ".join(x.split())
    return x


def normalize_column_name(name):
    value = unicodedata.normalize("NFKD", str(name or ""))
    value = value.encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return value.strip("_")


def normalize_columns(df):
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    return df


def first_column(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def numeric_columns(df, excluded=None):
    excluded = set(excluded or [])
    columns = []

    for col in df.columns:
        if col in excluded:
            continue

        values = df[col].dropna().head(20)
        if values.empty:
            continue

        parsed = values.apply(parse_amount)
        if (parsed != 0).any():
            columns.append(col)

    return columns


def first_text_column(df, excluded=None):
    excluded = set(excluded or [])

    for col in df.columns:
        if col in excluded:
            continue

        values = df[col].dropna().head(20)
        if values.empty:
            continue

        parsed = values.apply(parse_amount)
        if not (parsed != 0).any():
            return col

    return None


def parse_amount(value):
    if pd.isna(value):
        return 0.0

    raw = str(value).strip()
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.replace("$", "").replace(",", "").replace("(", "").replace(")", "")
    amount = pd.to_numeric(raw, errors="coerce")

    if pd.isna(amount):
        return 0.0

    return float(-amount if negative else amount)


def parse_date(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def row_text_sample(df, limit=20):
    if df.empty:
        return ""
    return " ".join(
        " ".join(str(value).lower() for value in row.values)
        for _, row in df.head(limit).iterrows()
    )


def detect_file_type(df, filename, requested_type=None):
    normalized = normalize_columns(df)
    cols = set(normalized.columns)
    sample = row_text_sample(normalized)
    name = normalize_column_name(filename)

    if (
        "balance_sheet" in name
        or {"assets", "liabilities"}.issubset(cols)
        or "total assets" in sample
        or "current liabilities" in sample
        or "cash at bank" in sample
    ):
        return "balance_sheet"

    if (
        "cash_flow" in name
        or "cashflow" in name
        or "closing balance" in sample
        or "net cash" in sample
        or "cash_flow_type" in cols
    ):
        return "cash_flow"

    if (
        "general_ledger" in name
        or "ledger" in name
        or {"debit", "credit"}.intersection(cols)
        or "account" in cols and "transaction_date" in cols
    ):
        return "general_ledger"

    if (
        "income_statement" in name
        or "profit_loss" in name
        or "p_l" in name
        or "revenue" in sample
        or "gross profit" in sample
        or "net profit" in sample
    ):
        return "income_statement"

    if requested_type in VALID_DOC_TYPES:
        return requested_type

    return "income_statement"


def insert_upload(conn, filename, doc_type):
    row = conn.execute(text("""
        INSERT INTO uploads (filename, type)
        VALUES (:filename, :doc_type)
        RETURNING id
    """), {
        "filename": filename,
        "doc_type": doc_type,
    }).fetchone()
    return row[0]


def build_financial_records(df, doc_type):
    date_col = first_column(df, ["date", "transaction_date", "period"])
    amount_col = first_column(df, ["amount", "value", "total"])
    category_col = first_column(df, ["category", "account", "line_item", "description"])
    description_col = first_column(df, ["description", "memo", "details", "line_item", "category"])

    if not amount_col or not category_col:
        return []

    records = []
    for _, row in df.iterrows():
        category = clean_text(row.get(category_col))
        amount = parse_amount(row.get(amount_col))
        if not category:
            continue

        record = {
            "Date": parse_date(row.get(date_col)) if date_col else None,
            "Description": clean_text(row.get(description_col)) if description_col else category,
            "Category": category,
            "Amount": amount,
            "doc_type": doc_type,
        }
        record["fingerprint"] = generate_hash(record)
        records.append(record)

    return records


def insert_financial_data(conn, records):
    insert_stmt = text("""
        INSERT INTO financial_data
        (date, description, category, amount, doc_type, fingerprint)
        VALUES (:Date, :Description, :Category, :Amount, :doc_type, :fingerprint)
        ON CONFLICT (fingerprint) DO NOTHING
    """)

    rows_inserted = 0
    for record in records:
        result = conn.execute(insert_stmt, record)
        rows_inserted += max(result.rowcount or 0, 0)

    return rows_inserted


def infer_balance_section(line_item):
    value = clean_text(line_item)
    if "current asset" in value or "cash" in value or "receivable" in value or "inventory" in value:
        return "current_assets"
    if "asset" in value:
        return "non_current_assets"
    if "current liabil" in value or "payable" in value or "credit card" in value:
        return "current_liabilities"
    if "liabil" in value or "loan" in value or "debt" in value:
        return "non_current_liabilities"
    if "equity" in value:
        return "equity"
    return None


def is_revenue_line(line_item, category=None):
    text_value = f"{clean_text(line_item)} {clean_text(category)}"
    revenue_terms = (
        "revenue",
        "sales",
        "turnover",
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
    return (
        any(term in text_value for term in revenue_terms)
        and not any(term in text_value for term in excluded_terms)
    )


def insert_typed_rows(conn, upload_id, doc_type, df):
    amount_col = first_column(df, [
        "amount",
        "value",
        "total",
        "balance",
        "closing_balance",
        "closing_cash_balance",
        "net_cash_flow",
        "net_cash",
        "net",
        "cash_flow",
        "cashflow",
    ])
    date_col = first_column(df, ["date", "period", "month", "as_of_date", "statement_date", "transaction_date"])
    line_col = first_column(df, [
        "line_item",
        "category",
        "account",
        "description",
        "name",
        "item",
        "particulars",
        "activity",
        "cash_flow_item",
        "cashflow_item",
    ])
    if not line_col:
        line_col = first_text_column(df, {date_col, amount_col})

    if doc_type == "general_ledger":
        description_col = first_column(df, ["description", "memo", "details"])
        account_col = first_column(df, ["account", "account_name"])
        category_col = first_column(df, ["category", "type"])
        debit_col = first_column(df, ["debit"])
        credit_col = first_column(df, ["credit"])

        if not amount_col and not debit_col and not credit_col:
            raise HTTPException(
                status_code=400,
                detail="CSV must include amount, debit, or credit columns",
            )

        rows = []
        for _, row in df.iterrows():
            debit = parse_amount(row.get(debit_col)) if debit_col else 0.0
            credit = parse_amount(row.get(credit_col)) if credit_col else 0.0
            amount = parse_amount(row.get(amount_col)) if amount_col else debit - credit
            rows.append({
                "upload_id": upload_id,
                "transaction_date": parse_date(row.get(date_col)) if date_col else None,
                "description": str(row.get(description_col) or ""),
                "account": str(row.get(account_col) or ""),
                "category": clean_text(row.get(category_col) or row.get(account_col)),
                "debit": debit,
                "credit": credit,
                "amount": amount,
                "fingerprint": hashlib.sha256(str(row.to_dict()).encode()).hexdigest(),
            })

        if rows:
            conn.execute(text("""
                INSERT INTO general_ledger
                (upload_id, transaction_date, description, account, category, debit, credit, amount, fingerprint)
                VALUES (:upload_id, :transaction_date, :description, :account, :category, :debit, :credit, :amount, :fingerprint)
            """), rows)
        return len(rows)

    if not line_col:
        raise HTTPException(status_code=400, detail="CSV must include a line item/category/description column")

    cash_in_col = first_column(df, [
        "cash_in",
        "inflow",
        "inflows",
        "receipts",
        "cash_receipts",
        "money_in",
    ])
    cash_out_col = first_column(df, [
        "cash_out",
        "outflow",
        "outflows",
        "payments",
        "cash_payments",
        "money_out",
    ])
    ignored_numeric_cols = {
        date_col,
        line_col,
        "category",
        "account",
        "description",
        "name",
        "item",
        "particulars",
        "activity",
        "section",
        "type",
        "cash_flow_type",
    }
    wide_amount_cols = []

    if not amount_col and doc_type == "cash_flow" and (cash_in_col or cash_out_col):
        amount_col = None
    elif not amount_col:
        wide_amount_cols = numeric_columns(df, ignored_numeric_cols)

    if not amount_col and not wide_amount_cols and not (doc_type == "cash_flow" and (cash_in_col or cash_out_col)):
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must include an amount/value column, cash in/out columns, "
                "or monthly numeric columns"
            ),
        )

    rows = []
    for _, row in df.iterrows():
        line_item = str(row.get(line_col) or "").strip()
        if not line_item:
            continue

        if doc_type == "cash_flow" and not amount_col and (cash_in_col or cash_out_col):
            amounts = [(
                parse_date(row.get(date_col)) if date_col else None,
                parse_amount(row.get(cash_in_col)) - parse_amount(row.get(cash_out_col)),
            )]
        elif wide_amount_cols:
            amounts = [
                (parse_date(col), parse_amount(row.get(col)))
                for col in wide_amount_cols
            ]
        else:
            amounts = [(
                parse_date(row.get(date_col)) if date_col else None,
                parse_amount(row.get(amount_col)),
            )]

        for period, amount in amounts:
            item = {
                "upload_id": upload_id,
                "line_item": line_item,
                "amount": amount,
            }

            if doc_type == "income_statement":
                item["period"] = period
                item["category"] = clean_text(row.get("category") or line_item)
            elif doc_type == "cash_flow":
                item["period"] = period
                item["cash_flow_type"] = clean_text(row.get("cash_flow_type") or row.get("type") or line_item)
            else:
                item["as_of_date"] = period
                item["section"] = clean_text(row.get("section")) or infer_balance_section(line_item)

            rows.append(item)

    if not rows:
        return 0

    if doc_type == "income_statement":
        nonzero_rows = [row for row in rows if row["amount"] != 0]
        has_revenue = any(
            is_revenue_line(row["line_item"], row.get("category"))
            for row in nonzero_rows
        )

        if not nonzero_rows:
            raise HTTPException(
                status_code=400,
                detail="Income statement upload has no numeric values to ingest",
            )

        if not has_revenue:
            raise HTTPException(
                status_code=400,
                detail="Income statement must include a revenue, sales, or turnover line",
            )

    if doc_type == "income_statement":
        conn.execute(text("""
            INSERT INTO income_statement (upload_id, period, line_item, category, amount)
            VALUES (:upload_id, :period, :line_item, :category, :amount)
        """), rows)
    elif doc_type == "cash_flow":
        conn.execute(text("""
            INSERT INTO cash_flow (upload_id, period, line_item, cash_flow_type, amount)
            VALUES (:upload_id, :period, :line_item, :cash_flow_type, :amount)
        """), rows)
    else:
        conn.execute(text("""
            INSERT INTO balance_sheet (upload_id, as_of_date, line_item, section, amount)
            VALUES (:upload_id, :as_of_date, :line_item, :section, :amount)
        """), rows)

    return len(rows)

# -------------------------
# HASH
# -------------------------
def generate_hash(row):
    raw = "|".join([
        str(row.get("Date", "")),
        str(row.get("Category", "")),
        f"{round(float(row.get('Amount', 0)), 2)}",
        str(row.get("Description", ""))
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

# -------------------------
# REQUEST MODEL
# -------------------------
class SimulationInput(BaseModel):
    overrides: Optional[Dict[str, float]] = None

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "OpenFintel backend running"}

# -------------------------
# UPLOAD API (FIXED)
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    try:
        df = pd.read_csv(file.file)

        df = df.replace(r'^\s*$', None, regex=True)
        df = df.dropna(how="all")
        df = normalize_columns(df)

        if df.empty:
            raise HTTPException(status_code=400, detail="CSV has no usable rows")

        detected_type = detect_file_type(df, file.filename or "", doc_type)
        rows_uploaded = len(df)

        with engine.begin() as conn:
            upload_id = insert_upload(conn, file.filename, detected_type)
            rows_inserted = insert_typed_rows(conn, upload_id, detected_type, df)

            legacy_records = build_financial_records(df, detected_type)
            if legacy_records and detected_type in {"income_statement", "general_ledger"}:
                insert_financial_data(conn, legacy_records)

            # Log both parsed rows and inserted rows for the upload summary.
            conn.execute(text("""
                INSERT INTO upload_logs (filename, doc_type, rows_uploaded, rows_inserted)
                VALUES (:f, :d, :u, :i)
            """), {
                "f": file.filename,
                "d": detected_type,
                "u": rows_uploaded,
                "i": rows_inserted
            })

        return {
            "uploaded": rows_uploaded,
            "inserted": rows_inserted,
            "type": detected_type
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# KPI API
# -------------------------
@app.get("/api/kpis")
def get_kpis():
    try:
        with engine.begin() as conn:
            return calculate_kpis(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# DASHBOARD API
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    try:
        with engine.begin() as conn:

            rows = conn.execute(text("""
                SELECT category, amount
                FROM financial_data
                WHERE doc_type = 'income_statement'
            """)).fetchall()

            monthly_rows = conn.execute(text("""
                SELECT 
                    DATE_TRUNC('month', date) as month,

                    SUM(CASE 
                        WHEN amount > 0 THEN amount 
                        ELSE 0 
                    END) as revenue,

                    SUM(CASE 
                        WHEN amount < 0 THEN ABS(amount) 
                        ELSE 0 
                    END) as expenses

                FROM financial_data
                WHERE doc_type = 'income_statement'
                AND date IS NOT NULL
                GROUP BY month
                ORDER BY month
            """)).fetchall()

        if not rows:
            return {"summary": {}, "graph": {}, "monthly": []}

        mapped_rows = [
            {"category": str(r[0] or ""), "amount": float(r[1] or 0)}
            for r in rows
        ]

        drivers = map_db_to_engine(mapped_rows)
        result = run_engine(drivers)

        kpis = result.get("kpis", {})

        monthly_data = [
            {
                "month": r[0].strftime("%Y-%m"),
                "revenue": float(r[1] or 0),
                "expenses": float(r[2] or 0),
                "profit": float((r[1] or 0) - (r[2] or 0))
            }
            for r in monthly_rows if r[0] is not None
        ]

        return {
            "summary": {
                "revenue": kpis.get("revenue", 0),
                "expenses": kpis.get("operating_expenses", 0),
                "net_profit": kpis.get("net_profit", 0),
                "gross_margin": (
                    kpis.get("gross_margin", 0) / kpis.get("revenue", 1)
                    if kpis.get("revenue", 0) else 0
                )
            },
            "graph": result.get("graph", {}),
            "monthly": monthly_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# FILES API
# -------------------------
@app.get("/api/files")
def get_files():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT filename, doc_type, rows_uploaded, rows_inserted, created_at
            FROM upload_logs
            ORDER BY created_at DESC
        """)).fetchall()

    return {
        "data": [
            {
                "filename": r[0],
                "doc_type": r[1],
                "rows_uploaded": r[2],
                "rows_inserted": r[3],
                "created_at": str(r[4])
            }
            for r in rows
        ]
    }

# -------------------------
# COVERAGE API
# -------------------------
@app.get("/api/coverage")
def get_coverage():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT doc_type, COALESCE(SUM(rows_inserted), 0) as records
            FROM upload_logs
            WHERE doc_type IS NOT NULL
            GROUP BY doc_type
            ORDER BY doc_type
        """)).fetchall()

    return {
        "data": [
            {"doc_type": r[0], "records": r[1]}
            for r in rows
        ]
    }
