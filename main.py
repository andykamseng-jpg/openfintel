from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, Optional
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
# INCOME STATEMENT CHECK BLOCK (YOUR TARGET)
# -------------------------
def validate_income_statement_rows(rows):
    nonzero_rows = [row for row in rows if row["amount"] != 0]

    has_income_statement_lines = any(
        is_income_statement_line(row["line_item"], row.get("category"))
        for row in nonzero_rows
    )

    if not nonzero_rows:
        raise HTTPException(
            status_code=400,
            detail="Income statement upload has no numeric values to ingest",
        )

    if not has_income_statement_lines:
        raise HTTPException(
            status_code=400,
            detail="Income statement must include revenue, sales, turnover, expense, or cost lines",
        )

# -------------------------
# HELPERS
# -------------------------
def is_income_statement_line(line_item, category=None):
    text_value = f"{clean_text(line_item)} {clean_text(category)}"

    income_statement_terms = (
        "revenue",
        "sales",
        "turnover",
        "service fees",
        "service revenue",
        "expense",
        "expenses",
        "cost",
        "cogs",
        "wages",
        "salary",
        "rent",
        "utilities",
        "insurance",
        "tax",
        "depreciation",
        "amortisation",
        "amortization",
    )

    return any(term in text_value for term in income_statement_terms)

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "OpenFintel backend running"}