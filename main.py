from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from sqlalchemy import create_engine, text
import os, re, unicodedata, hashlib

from services.kpi_service import calculate_engine_result, calculate_kpis

app = FastAPI()

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://www.openfintel.com",
        "https://openfintel-nine.vercel.app",
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
# CLEAN / NORMALIZE
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

def numeric_columns(df, excluded=None):
    excluded = set(excluded or [])
    cols = []
    for col in df.columns:
        if col in excluded:
            continue
        values = df[col].dropna().head(20)
        if values.empty:
            continue
        parsed = values.apply(parse_amount)
        if (parsed != 0).any():
            cols.append(col)
    return cols

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

# -------------------------
# LOGIC HELPERS
# -------------------------
def is_income_statement_line(line_item, category=None):
    text_value = f"{clean_text(line_item)} {clean_text(category)}"

    terms = (
        "revenue","sales","turnover","service fees","service revenue",
        "expense","expenses","cost","cogs","wages","salary",
        "rent","utilities","insurance","tax",
        "depreciation","amortisation","amortization"
    )
    return any(t in text_value for t in terms)

# -------------------------
# CORE INSERT
# -------------------------
def insert_typed_rows(conn, upload_id, doc_type, df):
    amount_col = first_column(df, ["amount", "value", "total"])
    date_col = first_column(df, ["date", "period"])
    line_col = first_column(df, ["line_item", "category", "account", "description"])

    if not line_col:
        line_col = first_text_column(df, {date_col, amount_col})

    if not line_col:
        raise HTTPException(status_code=400, detail="Missing line item column")

    rows = []

    for _, row in df.iterrows():
        line_item = str(row.get(line_col) or "").strip()
        if not line_item:
            continue

        amount = parse_amount(row.get(amount_col))

        rows.append({
            "upload_id": upload_id,
            "line_item": line_item,
            "amount": amount,
            "period": parse_date(row.get(date_col)) if date_col else None,
            "category": clean_text(row.get("category") or line_item),
        })

    if not rows:
        return 0

    # -------------------------
    # ✅ YOUR FIX (ADDED HERE)
    # -------------------------
    if doc_type == "income_statement":
        nonzero_rows = [row for row in rows if row["amount"] != 0]

        if not nonzero_rows:
            raise HTTPException(
                status_code=400,
                detail="Income statement upload has no numeric values to ingest",
            )

        has_income_statement_lines = any(
            is_income_statement_line(row["line_item"], row.get("category"))
            for row in nonzero_rows
        )

        if not has_income_statement_lines:
            raise HTTPException(
                status_code=400,
                detail="Income statement must include revenue, sales, turnover, expense, or cost lines",
            )

    # -------------------------
    # INSERT
    # -------------------------
    if doc_type == "income_statement":
        conn.execute(text("""
            INSERT INTO income_statement (upload_id, period, line_item, category, amount)
            VALUES (:upload_id, :period, :line_item, :category, :amount)
        """), rows)

    return len(rows)

# -------------------------
# API
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    try:
        df = pd.read_csv(file.file)
        df = df.dropna(how="all")
        df = normalize_columns(df)

        if df.empty:
            raise HTTPException(status_code=400, detail="Empty CSV")

        with engine.begin() as conn:
            upload_id = 1  # simplified
            inserted = insert_typed_rows(conn, upload_id, doc_type, df)

        return {"inserted": inserted}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"status": "running"}
# -------------------------
# KPI API (SAFE)
# -------------------------
@app.get("/api/kpis")
def get_kpis():
    try:
        with engine.begin() as conn:
            return calculate_kpis(conn)
    except Exception as e:
        return {
            "cash_position": 0,
            "liquidity_ratio": 0,
            "debt_ratio": 0,
            "burn_rate": 0,
            "working_capital": 0,
            "error": str(e)
        }


# -------------------------
# DASHBOARD API (SAFE)
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    try:
        with engine.begin() as conn:
            result = calculate_engine_result(conn)

        return {
            "summary": result.get("summary", {}),
            "graph": result.get("summary", {}),
            "monthly": []
        }

    except Exception as e:
        return {
            "summary": {
                "revenue": 0,
                "expenses": 0,
                "net_profit": 0,
                "gross_margin": 0
            },
            "graph": {},
            "monthly": [],
            "error": str(e)
        }