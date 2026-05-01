
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
import os, unicodedata, hashlib

from engine.adapter import run_engine
from engine.mapper import map_db_to_engine

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

        required_cols = {"Date", "Amount", "Category", "Description"}
        if not required_cols.issubset(df.columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must include columns: {required_cols}"
            )

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

        df["Category"] = df["Category"].apply(clean_text)
        df["Description"] = df["Description"].apply(clean_text)

        df = df[
            df["Date"].notna() &
            df["Amount"].notna() &
            (df["Category"] != "")
        ]

        rows_uploaded = len(df)

        df["fingerprint"] = df.apply(generate_hash, axis=1)
        records = df.to_dict(orient="records")

        with engine.begin() as conn:

            # ✅ INSERT + RETURN actual inserted rows
            result = conn.execute(text("""
                INSERT INTO financial_data
                (date, description, category, amount, doc_type, fingerprint)
                VALUES (:Date, :Description, :Category, :Amount, :doc_type, :fingerprint)
                ON CONFLICT (fingerprint) DO NOTHING
                RETURNING 1
            """), [
                {
                    "Date": r["Date"],
                    "Description": r["Description"],
                    "Category": r["Category"],
                    "Amount": float(r["Amount"]),
                    "doc_type": doc_type,
                    "fingerprint": r["fingerprint"]
                }
                for r in records
            ])

            rows_inserted = len(result.fetchall())

            # ✅ LOG correct values
            conn.execute(text("""
                INSERT INTO upload_logs (filename, doc_type, rows_uploaded, rows_inserted)
                VALUES (:f, :d, :u, :i)
            """), {
                "f": file.filename,
                "d": doc_type,
                "u": rows_uploaded,
                "i": rows_inserted
            })

        return {
            "uploaded": rows_uploaded,
            "inserted": rows_inserted
        }

    except HTTPException:
        raise
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
            SELECT doc_type, COUNT(*) as count
            FROM financial_data
            GROUP BY doc_type
        """)).fetchall()

    return {
        "data": [
            {"doc_type": r[0], "records": r[1]}
            for r in rows
        ]
    }
