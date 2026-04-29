```python
from fastapi import FastAPI, UploadFile, Form
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
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# DATABASE
# -------------------------
engine = create_engine(os.getenv("DATABASE_URL"))

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
# HASH (DEDUP)
# -------------------------
def generate_hash(row):
    raw = "|".join([
        str(row["Date"]),
        row["Category"],
        f"{round(row['Amount'], 2)}",
        row["Description"]
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

# -------------------------
# REQUEST MODEL (SIMULATION)
# -------------------------
class SimulationInput(BaseModel):
    overrides: Optional[Dict[str, float]] = None

# -------------------------
# UPLOAD API
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    df = pd.read_csv(file.file)

    df = df.replace(r'^\s*$', None, regex=True)
    df = df.dropna(how="all")

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

        conn.execute(text("""
            INSERT INTO financial_data
            (date, description, category, amount, doc_type, fingerprint)
            VALUES (:Date, :Description, :Category, :Amount, :doc_type, :fingerprint)
            ON CONFLICT (fingerprint) DO NOTHING
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

        conn.execute(text("""
            INSERT INTO upload_logs (filename, doc_type, rows_uploaded, rows_inserted)
            VALUES (:f, :d, :u, :i)
        """), {
            "f": file.filename,
            "d": doc_type,
            "u": rows_uploaded,
            "i": rows_uploaded
        })

    return {"uploaded": rows_uploaded}

# -------------------------
# DASHBOARD API
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT category, amount
            FROM financial_data
            WHERE doc_type = 'income_statement'
        """)).fetchall()

    if not rows:
        return {
            "summary": {},
            "graph": {},
            "monthly": []
        }

    mapped_rows = [
        {"category": str(r[0] or ""), "amount": float(r[1] or 0)}
        for r in rows
    ]

    drivers = map_db_to_engine(mapped_rows)
    result = run_engine(drivers)

    kpis = result["kpis"]

    return {
        "summary": {
            "revenue": kpis["revenue"],
            "expenses": kpis["operating_expenses"],
            "net_profit": kpis["net_profit"],
            "gross_margin": (
                kpis["gross_margin"] / kpis["revenue"]
                if kpis["revenue"] else 0
            )
        },
        "graph": result["graph"],
        "monthly": []
    }

# -------------------------
# SIMULATION API (NEW 🔥)
# -------------------------
@app.post("/api/simulate")
def simulate(data: SimulationInput):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT category, amount
            FROM financial_data
            WHERE doc_type = 'income_statement'
        """)).fetchall()

    if not rows:
        return {
            "summary": {},
            "graph": {}
        }

    mapped_rows = [
        {"category": str(r[0] or ""), "amount": float(r[1] or 0)}
        for r in rows
    ]

    drivers = map_db_to_engine(mapped_rows)

    result = run_engine(
        drivers,
        overrides=data.overrides
    )

    kpis = result["kpis"]

    return {
        "summary": {
            "revenue": kpis["revenue"],
            "expenses": kpis["operating_expenses"],
            "net_profit": kpis["net_profit"],
            "gross_margin": (
                kpis["gross_margin"] / kpis["revenue"]
                if kpis["revenue"] else 0
            )
        },
        "graph": result["graph"]
    }

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
            {
                "doc_type": r[0],
                "records": r[1]
            }
            for r in rows
        ]
    }
```
