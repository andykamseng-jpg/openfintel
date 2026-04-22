from fastapi import FastAPI, UploadFile, File, Form
import pandas as pd
import io

app = FastAPI()

# In-memory storage
storage = {}

# -----------------------------
# Load CSV safely
# -----------------------------
def load_csv(file: UploadFile):
    content = file.file.read()
    df = pd.read_csv(io.BytesIO(content))

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    # Print for debugging
    print("Detected columns:", df.columns.tolist())

    # Smart mapping
    item_candidates = ["item", "category", "description", "account", "name"]
    amount_candidates = ["amount", "value", "total", "balance", "net"]

    item_col = None
    amount_col = None

    for col in df.columns:
        if col in item_candidates:
            item_col = col
        if col in amount_candidates:
            amount_col = col

    # Fallback: assume first column = item, second = amount
    if not item_col and len(df.columns) >= 1:
        item_col = df.columns[0]

    if not amount_col and len(df.columns) >= 2:
        amount_col = df.columns[1]

    # Rename to standard
    df = df.rename(columns={
        item_col: "item",
        amount_col: "amount"
    })

    return df


# -----------------------------
# INCOME STATEMENT ENGINE
# -----------------------------
def process_income_statement(df):

    if "amount" not in df.columns or "item" not in df.columns:
        return {"error": "CSV must contain 'Item' and 'Amount'"}

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["item"] = df["item"].astype(str)

    revenue = df[df["amount"] > 0]["amount"].sum()
    expenses = abs(df[df["amount"] < 0]["amount"].sum())

    # Detect COGS safely
    cogs_keywords = ["cogs", "cost of goods", "food", "beverage"]
    cogs = df[
        df["item"].str.lower().str.contains("|".join(cogs_keywords), na=False)
    ]["amount"].abs().sum()

    operating_expenses = expenses - cogs

    gross_profit = revenue - cogs
    net_profit = revenue - expenses

    gross_margin = gross_profit / revenue if revenue > 0 else 0

    return {
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "operating_expenses": round(operating_expenses, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "gross_margin": round(gross_margin, 2),
        "category_breakdown": df.groupby("item")["amount"].sum().to_dict()
    }


# -----------------------------
# CASHFLOW ENGINE (UPGRADED)
# -----------------------------
def process_cashflow(df):

    inflow_cols = ["inflow", "cash in", "credit"]
    outflow_cols = ["outflow", "cash out", "debit"]

    inflow_col = next((c for c in inflow_cols if c in df.columns), None)
    outflow_col = next((c for c in outflow_cols if c in df.columns), None)

    if inflow_col and outflow_col:
        inflow = pd.to_numeric(df[inflow_col], errors="coerce").fillna(0).sum()
        outflow = pd.to_numeric(df[outflow_col], errors="coerce").fillna(0).sum()
        net_cashflow = inflow - outflow

    elif "amount" in df.columns:
        net_cashflow = pd.to_numeric(df["amount"], errors="coerce").fillna(0).sum()

    else:
        return {"error": "Cashflow file must contain Inflow/Outflow or Amount column"}

    return {
        "net_cashflow": round(net_cashflow, 2)
    }


# -----------------------------
# UPLOAD API
# -----------------------------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), doc_type: str = Form(...)):

    df = load_csv(file)

    if doc_type not in ["income_statement", "expenses", "cashflow"]:
        return {"error": "Invalid doc_type"}

    storage[doc_type] = df

    return {"message": f"{doc_type} uploaded successfully"}


# -----------------------------
# DASHBOARD API
# -----------------------------
@app.get("/api/dashboard")
def dashboard():

    try:
        if "income_statement" not in storage:
            return {"error": "Upload income_statement first"}

        income_data = process_income_statement(storage["income_statement"])

        # If processing failed
        if "error" in income_data:
            return income_data

        result = {
            "revenue": income_data["revenue"],
            "cogs": income_data["cogs"],
            "operating_expenses": income_data["operating_expenses"],
            "gross_profit": income_data["gross_profit"],
            "net_profit": income_data["net_profit"],
            "gross_margin": income_data["gross_margin"],
            "category_breakdown": income_data["category_breakdown"]
        }

        # Add cashflow if available
        if "cashflow" in storage:
            cashflow_data = process_cashflow(storage["cashflow"])
            result["cashflow"] = cashflow_data

        return result

    except Exception as e:
        return {"error": str(e)}