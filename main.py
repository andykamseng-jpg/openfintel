from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os, unicodedata, hashlib

# 🔥 ENGINE IMPORT
from engine.compute import compute_kpis

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
# DB
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
# DRIVER MAPPING (CRITICAL)
# -------------------------
def map_to_drivers(rows):
    drivers = {
        "revenue": 0,

        # COGS
        "raw_materials": 0,
        "supplier_cost": 0,
        "waste": 0,

        # OPEX
        "rent": 0,
        "wages": 0,
        "utilities": 0,
    }

    for r in rows:
        cat = (r["category"] or "").lower()
        amt = float(r["amount"] or 0)

        # -------------------------
        # REVENUE
        # -------------------------
        if any(k in cat for k in ["sales", "revenue", "income"]):
            drivers["revenue"] += abs(amt)

        # -------------------------
        # COGS
        # -------------------------
        elif any(k in cat for k in ["ingredient", "raw", "material", "food"]):
            drivers["raw_materials"] += abs(amt)

        elif "supplier" in cat:
            drivers["supplier_cost"] += abs(amt)

        elif any(k in cat for k in ["waste", "spoil", "loss"]):
            drivers["waste"] += abs(amt)

        # -------------------------
        # OPEX
        # -------------------------
        elif "rent" in cat:
            drivers["rent"] += abs(amt)

        elif any(k in cat for k in ["salary", "wage", "staff"]):
            drivers["wages"] += abs(amt)

        elif any(k in cat for k in ["utility", "electric", "water"]):
            drivers["utilities"] += abs(amt)

    return drivers

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
# DASHBOARD (FIXED ENGINE)
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT category, amount
            FROM financial_data
        """)).fetchall()

    mapped = [
        {"category": r[0], "amount": r[1]}
        for r in rows
    ]

    drivers = map_to_drivers(mapped)

    # 🔥 CORE ENGINE
    kpis = compute_kpis(drivers)

    return {
        "summary": {
            "revenue": kpis.get("revenue", 0),
            "expenses": kpis.get("operating_expenses", 0),
            "net_profit": kpis.get("net_profit", 0),
            "gross_margin": (
                kpis.get("gross_margin", 0) / kpis.get("revenue", 1)
            )
        },
        "graph": kpis
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