from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os, unicodedata, hashlib

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
def generate_hash(df):
    return (
        df["Date"].astype(str) + "|" +
        df["Category"] + "|" +
        df["Amount"].round(2).astype(str) + "|" +
        df["Description"]
    ).apply(lambda x: hashlib.sha256(x.encode()).hexdigest())

# -------------------------
# NORMALIZE PER REPORT TYPE
# -------------------------
def normalize(df, doc_type):

    df.columns = df.columns.str.strip()

    if doc_type == "income_statement":
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    elif doc_type == "general_ledger":
        df["Debit"] = pd.to_numeric(df.get("Debit", 0), errors="coerce").fillna(0)
        df["Credit"] = pd.to_numeric(df.get("Credit", 0), errors="coerce").fillna(0)
        df["Amount"] = df["Debit"] - df["Credit"]
        df["Category"] = df.get("Account", "").apply(clean_text)

    elif doc_type == "balance_sheet":
        df["Amount"] = pd.to_numeric(df.get("Value", 0), errors="coerce")
        df["Category"] = df.get("Asset", "").apply(clean_text)

    elif doc_type == "cash_flow":
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    elif doc_type == "expense_breakdown":
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    else:
        raise ValueError("Unsupported doc_type")

    return df

# -------------------------
# UPLOAD ENDPOINT
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):

    df = pd.read_csv(file.file)

    # Clean empty rows
    df = df.replace(r'^\s*$', None, regex=True)
    df = df.dropna(how="all")
    df = df.loc[~df.apply(lambda r: r.astype(str).str.strip().eq("").all(), axis=1)]

    # Normalize date
    df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce").dt.date

    # Clean text fields safely
    if "Category" in df.columns:
        df["Category"] = df["Category"].apply(clean_text)
    if "Description" in df.columns:
        df["Description"] = df["Description"].apply(clean_text)
    else:
        df["Description"] = ""

    # Apply report-specific logic
    df = normalize(df, doc_type)

    # Validation
    df = df[
        df["Date"].notna() &
        df["Amount"].notna() &
        (df["Category"] != "") &
        (df["Amount"].abs() > 0.000001)
    ]

    rows_uploaded = len(df)

    # Fingerprint
    df["fingerprint"] = generate_hash(df)

    records = df.to_dict(orient="records")

    with engine.begin() as conn:

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

        inserted = len(result.fetchall())

        conn.execute(text("""
            INSERT INTO upload_logs (filename, doc_type, rows_uploaded, rows_inserted)
            VALUES (:f, :d, :u, :i)
        """), {
            "f": file.filename,
            "d": doc_type,
            "u": rows_uploaded,
            "i": inserted
        })

    return {
        "uploaded": rows_uploaded,
        "inserted": inserted
    }

# -------------------------
# SUMMARY (Income Statement)
# -------------------------
@app.get("/api/summary")
def summary():

    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT
                SUM(CASE WHEN category = 'revenue' THEN amount ELSE 0 END) AS revenue,
                SUM(CASE WHEN category = 'expenses' THEN amount ELSE 0 END) AS expenses
            FROM financial_data
            WHERE doc_type = 'income_statement'
        """)).fetchone()

    revenue = float(result[0] or 0)
    expenses = float(result[1] or 0)

    return {
        "revenue": revenue,
        "expenses": expenses,
        "net_profit": revenue - expenses,
        "gross_margin": ((revenue - expenses) / revenue) if revenue else 0
    }

# -------------------------
# CASH FLOW API
# -------------------------
@app.get("/api/cashflow")
def cashflow():

    with engine.begin() as conn:
        total = conn.execute(text("""
            SELECT SUM(amount)
            FROM financial_data
            WHERE doc_type = 'cash_flow'
        """)).scalar()

    return {"cash_flow": float(total or 0)}

# -------------------------
# BALANCE SHEET SNAPSHOT
# -------------------------
@app.get("/api/balance-sheet")
def balance_sheet():

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT category, SUM(amount)
            FROM financial_data
            WHERE doc_type = 'balance_sheet'
            GROUP BY category
        """)).fetchall()

    return {r[0]: float(r[1]) for r in rows}

# -------------------------
# MONTHLY ANALYTICS
# -------------------------
@app.get("/api/monthly")
def monthly():

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                DATE_TRUNC('month', date) as month,
                SUM(CASE WHEN category = 'revenue' THEN amount ELSE 0 END) AS revenue,
                SUM(CASE WHEN category = 'expenses' THEN amount ELSE 0 END) AS expenses
            FROM financial_data
            WHERE doc_type = 'income_statement'
            GROUP BY month
            ORDER BY month
        """)).fetchall()

    return [
        {
            "month": str(r[0]),
            "revenue": float(r[1]),
            "expenses": float(r[2]),
            "profit": float(r[1] - r[2])
        }
        for r in rows
    ]