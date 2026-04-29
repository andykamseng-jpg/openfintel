from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os, unicodedata, hashlib

# 🔥 ENGINE
from engine.adapter import run_engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# CATEGORY CLASSIFIER 🔥
# -------------------------
def classify_category(cat: str):
    cat = (cat or "").lower()

    if any(k in cat for k in ["sales", "revenue", "income"]):
        return "revenue"

    if any(k in cat for k in ["ingredient", "inventory", "material", "cost of goods"]):
        return "cogs"

    if any(k in cat for k in ["rent", "wage", "salary", "utility", "expense"]):
        return "opex"

    return "other"

# -------------------------
# UPLOAD
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
# DASHBOARD 🔥 FULL ENGINE VERSION
# -------------------------
@app.get("/api/dashboard")
def dashboard():
    with engine.begin() as conn:

        # -------------------------
        # MONTHLY (KEEP EXISTING)
        # -------------------------
        rows = conn.execute(text("""
            SELECT
                DATE_TRUNC('month', date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS revenue,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) AS expenses
            FROM financial_data
            WHERE doc_type = 'income_statement'
            GROUP BY month
            ORDER BY month
        """)).fetchall()

        # -------------------------
        # 🔥 CATEGORY TOTALS
        # -------------------------
        totals = conn.execute(text("""
            SELECT category, SUM(amount) as total
            FROM financial_data
            WHERE doc_type = 'income_statement'
            GROUP BY category
        """)).fetchall()

    # -------------------------
    # PROCESS MONTHLY (UNCHANGED)
    # -------------------------
    monthly = []
    total_revenue = 0
    total_expenses = 0

    for r in rows:
        revenue = float(r[1] or 0)
        expenses = float(r[2] or 0)

        monthly.append({
            "month": str(r[0]),
            "revenue": revenue,
            "expenses": expenses,
            "profit": revenue - expenses
        })

        total_revenue += revenue
        total_expenses += expenses

    # -------------------------
    # 🔥 CLASSIFY INTO DRIVERS
    # -------------------------
    revenue = 0
    cogs = 0
    opex = 0

    for row in totals:
        category = row[0] or ""
        amount = float(row[1] or 0)

        bucket = classify_category(category)

        if bucket == "revenue":
            revenue += amount
        elif bucket == "cogs":
            cogs += abs(amount)
        elif bucket == "opex":
            opex += abs(amount)

    # -------------------------
    # 🔥 ENGINE INPUT MAPPING
    # -------------------------
    units = 1
    price = revenue if revenue else 0

    raw_data = {
        "units": units,
        "price": price,
        "variable_costs": cogs,
        "fixed_costs": opex,
        "pos": revenue,
        "supplier_payments": cogs,
    }

    # -------------------------
    # 🔥 RUN ENGINE
    # -------------------------
    result = run_engine(raw_data)

    # -------------------------
    # RESPONSE
    # -------------------------
    return {
        "summary": result["kpis"],   # ✅ KPI cards now engine-driven
        "monthly": monthly,          # unchanged
        "graph": result["graph"],    # future BAS UI
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