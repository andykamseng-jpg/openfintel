
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

# -------------------------
# HELPERS
# -------------------------
def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x)
    x = unicodedata.normalize("NFKD", x)
    x = x.encode("ascii", "ignore").decode()
    return " ".join(x.strip().lower().split())


def normalize_column_name(name):
    value = unicodedata.normalize("NFKD", str(name or ""))
    value = value.encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return value.strip("_")


def normalize_columns(df):
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    return df


def parse_amount(value):
    if pd.isna(value):
        return 0.0
    raw = str(value).replace("$", "").replace(",", "").strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    return float(pd.to_numeric(raw, errors="coerce") or 0)


def parse_date(value):
    d = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(d) else d.date()


def generate_hash(row):
    raw = "|".join([
        str(row.get("Date", "")),
        str(row.get("Category", "")),
        str(round(float(row.get("Amount", 0)), 2)),
        str(row.get("Description", ""))
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "OpenFintel backend running"}

# -------------------------
# UPLOAD API
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    try:
        df = pd.read_csv(file.file)
        df = df.dropna(how="all")
        df = normalize_columns(df)

        if df.empty:
            raise HTTPException(400, "Empty file")

        rows = []

        for _, r in df.iterrows():
            record = {
                "Date": parse_date(r.get("date")),
                "Description": clean_text(r.get("description")),
                "Category": clean_text(r.get("category") or r.get("account")),
                "Amount": parse_amount(r.get("amount") or r.get("debit") or 0)
                         - parse_amount(r.get("credit") or 0),
                "doc_type": doc_type,
            }

            if not record["Category"]:
                continue

            record["fingerprint"] = generate_hash(record)
            rows.append(record)

        if not rows:
            raise HTTPException(400, "No valid rows")

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO financial_data (date, description, category, amount, doc_type, fingerprint)
                VALUES (:Date, :Description, :Category, :Amount, :doc_type, :fingerprint)
                ON CONFLICT (fingerprint) DO NOTHING
            """), rows)

        return {"inserted": len(rows)}

    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------
# KPI API
# -------------------------
@app.get("/api/kpis")
def get_kpis():
    try:
        with engine.begin() as conn:
            return calculate_kpis(conn)
    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------
# DASHBOARD API
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    try:
        with engine.begin() as conn:
            result = calculate_engine_result(conn)
            summary = result.get("summary", {})

            monthly = conn.execute(text("""
                SELECT 
                    DATE_TRUNC('month', date) as m,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                FROM financial_data
                WHERE doc_type = 'income_statement'
                GROUP BY m
                ORDER BY m
            """)).fetchall()

        monthly_data = [
            {
                "month": str(r[0])[:7],
                "revenue": float(r[1] or 0),
                "expenses": float(r[2] or 0),
                "profit": float((r[1] or 0) - (r[2] or 0))
            }
            for r in monthly if r[0]
        ]

        return {
            "summary": summary,
            "graph": summary,
            "monthly": monthly_data
        }

    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------
# FILES
# -------------------------
@app.get("/api/files")
def files():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT filename, doc_type, rows_uploaded, rows_inserted, created_at
            FROM upload_logs
            ORDER BY created_at DESC
        """)).fetchall()

    return {"data": [dict(r._mapping) for r in rows]}

# -------------------------
# COVERAGE
# -------------------------
@app.get("/api/coverage")
def coverage():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT doc_type, COUNT(*) as records
            FROM financial_data
            GROUP BY doc_type
        """)).fetchall()

    return {"data": [dict(r._mapping) for r in rows]}
