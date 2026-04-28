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

# ✅ ONLY change: keep connection alive
engine = create_engine(
    os.getenv("DATABASE_URL"),
    pool_pre_ping=True
)

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
# SAFE COLUMN
# -------------------------
def safe_col(df, col):
    if col in df.columns:
        return df[col]
    return pd.Series([""] * len(df))

# -------------------------
# HASH
# -------------------------
def generate_hash(df):
    return (
        df["Date"].astype(str) + "|" +
        df["Category"] + "|" +
        df["Amount"].round(2).astype(str) + "|" +
        df["Description"]
    ).apply(lambda x: hashlib.sha256(x.encode()).hexdigest())

# -------------------------
# NORMALIZE
# -------------------------
def normalize(df, doc_type):

    df.columns = df.columns.str.strip()

    if doc_type == "income_statement":
        df["Amount"] = pd.to_numeric(safe_col(df, "Amount"), errors="coerce")
        df["Category"] = safe_col(df, "Category").apply(clean_text)

    elif doc_type == "general_ledger":
        debit = pd.to_numeric(safe_col(df, "Debit"), errors="coerce").fillna(0)
        credit = pd.to_numeric(safe_col(df, "Credit"), errors="coerce").fillna(0)
        df["Amount"] = debit - credit
        df["Category"] = safe_col(df, "Account").apply(clean_text)

    elif doc_type == "balance_sheet":
        df["Amount"] = pd.to_numeric(safe_col(df, "Value"), errors="coerce")
        df["Category"] = safe_col(df, "Asset").apply(clean_text)

    elif doc_type == "cash_flow":
        df["Amount"] = pd.to_numeric(safe_col(df, "Amount"), errors="coerce")
        df["Category"] = safe_col(df, "Category").apply(clean_text)

    elif doc_type == "expense_breakdown":
        df["Amount"] = pd.to_numeric(safe_col(df, "Amount"), errors="coerce")
        df["Category"] = safe_col(df, "Category").apply(clean_text)

    else:
        raise ValueError(f"Unsupported doc_type: {doc_type}")

    return df

# -------------------------
# SMALL SAFE BATCH (only fix for SSL issue)
# -------------------------
def chunked(data, size=50):
    for i in range(0, len(data), size):
        yield data[i:i + size]

# -------------------------
# UPLOAD
# -------------------------
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):

    try:
        df = pd.read_csv(file.file)

        df.columns = df.columns.str.strip()

        df = df.replace(r'^\s*$', None, regex=True)
        df = df.dropna(how="all")
        df = df.loc[~df.apply(lambda r: r.astype(str).str.strip().eq("").all(), axis=1)]

        df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce").dt.date

        if "Description" in df.columns:
            df["Description"] = df["Description"].apply(clean_text)
        else:
            df["Description"] = ""

        df = normalize(df, doc_type)

        df = df[
            df["Date"].notna() &
            df["Amount"].notna() &
            (df["Category"] != "") &
            (df["Amount"].abs() > 0.000001)
        ]

        rows_uploaded = len(df)

        df["fingerprint"] = generate_hash(df)
        records = df.to_dict(orient="records")

        inserted = 0

        with engine.begin() as conn:

            # ✅ ONLY CHANGE: batch insert to avoid SSL drop
            for batch in chunked(records, 50):

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
                    for r in batch
                ])

                inserted += len(result.fetchall())

            conn.execute(text("""
                INSERT INTO upload_logs (filename, doc_type, rows_uploaded, rows_inserted)
                VALUES (:f, :d, :u, :i)
            """), {
                "f": file.filename,
                "d": doc_type,
                "u": rows_uploaded,
                "i": inserted
            })

        return {"uploaded": rows_uploaded, "inserted": inserted}

    except Exception as e:
        return {"error": str(e)}

# -------------------------
# DASHBOARD
# -------------------------
@app.get("/api/dashboard")
def dashboard():

    with engine.begin() as conn:

        summary = conn.execute(text("""
            SELECT
                SUM(CASE WHEN category = 'revenue' THEN amount ELSE 0 END),
                SUM(CASE WHEN category = 'expenses' THEN amount ELSE 0 END)
            FROM financial_data
            WHERE doc_type = 'income_statement'
        """)).fetchone()

        monthly = conn.execute(text("""
            SELECT
                DATE_TRUNC('month', date),
                SUM(CASE WHEN category = 'revenue' THEN amount ELSE 0 END),
                SUM(CASE WHEN category = 'expenses' THEN amount ELSE 0 END)
            FROM financial_data
            WHERE doc_type = 'income_statement'
            GROUP BY 1
            ORDER BY 1
        """)).fetchall()

    revenue = float(summary[0] or 0)
    expenses = float(summary[1] or 0)
    profit = revenue - expenses

    return {
        "summary": {
            "revenue": revenue,
            "expenses": expenses,
            "net_profit": profit,
            "gross_margin": (profit / revenue) if revenue else 0
        },
        "monthly": [
            {
                "month": str(r[0]),
                "revenue": float(r[1]),
                "expenses": float(r[2]),
                "profit": float(r[1] - r[2])
            }
            for r in monthly
        ]
    }