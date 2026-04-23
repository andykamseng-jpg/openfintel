import os
import json
import pandas as pd
from fastapi import FastAPI, UploadFile, Form
from sqlalchemy import create_engine, text
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DATABASE (Neon)
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}
)

# Create table
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS uploads (
            id SERIAL PRIMARY KEY,
            doc_type TEXT,
            data JSONB
        )
    """))
    conn.commit()

# =========================
# HELPERS
# =========================
def detect_columns(df):
    cols = {c.lower(): c for c in df.columns}

    item_col = None
    amount_col = None

    for key in cols:
        if any(k in key for k in ["item", "description", "name", "category"]):
            item_col = cols[key]
        if any(k in key for k in ["amount", "value", "total"]):
            amount_col = cols[key]

    return item_col, amount_col


def process_income(df):
    item_col, amount_col = detect_columns(df)

    if not item_col or not amount_col:
        return {"error": "Cannot detect columns"}

    df = df[[item_col, amount_col]].dropna()
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    revenue = df[df[amount_col] > 0][amount_col].sum()

    cogs = abs(
        df[df[item_col].str.contains("cogs", case=False, na=False)][amount_col].sum()
    )

    expenses = abs(
        df[(df[amount_col] < 0) &
           (~df[item_col].str.contains("cogs", case=False, na=False))][amount_col].sum()
    )

    gross_profit = revenue - cogs
    net_profit = gross_profit - expenses
    margin = (gross_profit / revenue) if revenue else 0

    breakdown = df.groupby(item_col)[amount_col].sum().to_dict()

    return {
        "revenue": float(revenue),
        "cogs": float(cogs),
        "operating_expenses": float(expenses),
        "gross_profit": float(gross_profit),
        "net_profit": float(net_profit),
        "gross_margin": round(margin, 2),
        "category_breakdown": breakdown
    }


def process_cashflow(df):
    item_col, amount_col = detect_columns(df)

    if not item_col or not amount_col:
        return {"error": "Cannot detect columns"}

    df = df[[item_col, amount_col]].dropna()
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    inflow = df[df[amount_col] > 0][amount_col].sum()
    outflow = abs(df[df[amount_col] < 0][amount_col].sum())

    return {
        "cash_in": float(inflow),
        "cash_out": float(outflow),
        "net_cashflow": float(inflow - outflow)
    }

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"message": "OpenFintel API is running 🚀"}


@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    df = pd.read_csv(file.file)

    doc_type = doc_type.lower()

    if doc_type not in ["income_statement", "expenses", "cashflow"]:
        return {"error": "Invalid doc_type"}

    # ✅ Convert to JSON string for DB
    data = json.dumps(df.to_dict(orient="records"))

    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO uploads (doc_type, data) VALUES (:doc_type, :data)"),
            {"doc_type": doc_type, "data": data}
        )
        conn.commit()

    return {"message": f"{doc_type} uploaded successfully"}


@app.get("/api/dashboard")
def dashboard():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT doc_type, data FROM uploads ORDER BY id ASC")
        ).fetchall()

    income_data = []
    cashflow_data = []

    for row in rows:
        doc_type = row._mapping["doc_type"]
        data = row._mapping["data"]

        # ✅ Handle BOTH string and JSON
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data

        df = pd.DataFrame(parsed)

        if doc_type == "income_statement":
            income_data.append(process_income(df))

        elif doc_type == "cashflow":
            cashflow_data.append(process_cashflow(df))

    if not income_data:
        return {"error": "Upload income_statement first"}

    income = income_data[-1]
    cashflow = cashflow_data[-1] if cashflow_data else {}

    return {
        **income,
        "cashflow": cashflow
    }