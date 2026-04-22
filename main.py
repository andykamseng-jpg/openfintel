from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (for now)
storage = {}

# -----------------------------
# Utility: Flexible CSV parser
# -----------------------------
def load_csv(file: UploadFile):
    content = file.file.read()
    df = pd.read_csv(io.BytesIO(content))

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Try to map columns automatically
    col_map = {}

    for col in df.columns:
        if "item" in col or "name" in col or "category" in col:
            col_map["item"] = col
        if "amount" in col or "value" in col or "total" in col:
            col_map["amount"] = col

    if "item" not in col_map or "amount" not in col_map:
        raise ValueError("CSV must contain identifiable item and amount columns")

    df = df.rename(columns={
        col_map["item"]: "item",
        col_map["amount"]: "amount"
    })

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    return df

# -----------------------------
# Upload API
# -----------------------------
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    doc_type: str = Form(...)
):
    try:
        df = load_csv(file)

        valid_types = [
            "income_statement",
            "expenses",
            "cashflow",
            "balance_sheet",
            "general_ledger"
        ]

        if doc_type not in valid_types:
            return {"error": "Invalid doc_type"}

        storage[doc_type] = df

        return {"message": f"{doc_type} uploaded successfully"}

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Financial Engine
# -----------------------------
def compute_financials():
    if "income_statement" not in storage:
        return {"error": "Upload income_statement first"}

    df = storage["income_statement"]

    # Revenue = positive values
    revenue = df[df["amount"] > 0]["amount"].sum()

    # COGS = items containing "cogs"
    cogs = df[df["item"].str.lower().str.contains("cogs")]["amount"].abs().sum()

    # Operating expenses = negative values excluding COGS
    operating_expenses = df[
        (df["amount"] < 0) &
        (~df["item"].str.lower().str.contains("cogs"))
    ]["amount"].abs().sum()

    gross_profit = revenue - cogs
    net_profit = revenue - cogs - operating_expenses

    gross_margin = (gross_profit / revenue) if revenue > 0 else 0

    category_breakdown = df.groupby("item")["amount"].sum().to_dict()

    result = {
        "revenue": float(revenue),
        "cogs": float(cogs),
        "operating_expenses": float(operating_expenses),
        "gross_profit": float(gross_profit),
        "net_profit": float(net_profit),
        "gross_margin": round(gross_margin, 2),
        "category_breakdown": category_breakdown
    }

    # -----------------------------
    # Cashflow (optional)
    # -----------------------------
    if "cashflow" in storage:
        cf = storage["cashflow"]

        inflow = cf[cf["amount"] > 0]["amount"].sum()
        outflow = cf[cf["amount"] < 0]["amount"].abs().sum()

        result["cashflow"] = {
            "net_cashflow": float(inflow - outflow)
        }

    return result

# -----------------------------
# Dashboard API
# -----------------------------
@app.get("/api/dashboard")
def dashboard():
    return compute_financials()