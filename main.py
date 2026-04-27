from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os
import unicodedata

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ DB
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


# =========================
# 🔧 TEXT NORMALIZATION
# =========================
def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x)
    x = unicodedata.normalize("NFKD", x)
    x = x.encode("ascii", "ignore").decode()
    x = x.strip().lower()
    x = " ".join(x.split())
    return x


# =========================
# 🔧 CATEGORY STANDARDIZATION (KEY FIX)
# =========================
CATEGORY_MAP = {
    "delivery platform fees": "delivery sales",
    "dine-in revenue": "dine-in sales",
    "takeaway orders": "takeaway sales",
}

EXPECTED_CATEGORIES = {
    "dine-in sales",
    "takeaway sales",
    "delivery sales",
    "catering revenue",
    "food cogs",
    "beverage cogs",
    "kitchen labor",
    "foh labor",
    "marketing",
    "rent & utilities",
    "utilities"
}


# =========================
# 🏠 ROOT
# =========================
@app.get("/")
def root():
    return {"message": "OpenFintel API running 🚀"}


# =========================
# 📤 UPLOAD
# =========================
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    try:
        df = pd.read_csv(file.file)

        # Drop empty rows
        df = df.dropna(how="all")

        # Normalize columns
        df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce").dt.date
        df["Amount"] = pd.to_numeric(df.get("Amount"), errors="coerce")

        df["Category"] = df.get("Category", "").apply(clean_text)
        df["Description"] = df.get("Description", "").apply(clean_text)

        # Apply category mapping
        df["Category"] = df["Category"].apply(lambda x: CATEGORY_MAP.get(x, x))

        # Filter valid rows
        df = df[
            df["Date"].notna() &
            df["Amount"].notna() &
            (df["Category"].isin(EXPECTED_CATEGORIES)) &
            (df["Amount"].abs() > 0.000001)
        ]

        if df.empty:
            return {"error": "No valid data"}

        # 🔥 CRITICAL: AGGREGATE
        df = df.groupby(["Date", "Category"], as_index=False).agg({
            "Amount": "sum",
            "Description": "first"
        })

        start_date = df["Date"].min()
        end_date = df["Date"].max()

        records = df.to_dict(orient="records")

        # UPSERT
        with engine.begin() as conn:
            for row in records:
                conn.execute(
                    text("""
                        INSERT INTO financial_data
                        (date, description, category, amount, doc_type)
                        VALUES (:date, :desc, :cat, :amt, :doc)
                        ON CONFLICT (date, category, doc_type)
                        DO UPDATE SET
                            description = EXCLUDED.description,
                            amount = EXCLUDED.amount
                    """),
                    {
                        "date": row["Date"],
                        "desc": row["Description"],
                        "cat": row["Category"],
                        "amt": float(row["Amount"]),
                        "doc": doc_type
                    }
                )

            # Track uploads
            conn.execute(
                text("""
                    INSERT INTO uploaded_files
                    (file_name, doc_type, start_date, end_date)
                    VALUES (:name, :doc, :start, :end)
                """),
                {
                    "name": file.filename,
                    "doc": doc_type,
                    "start": start_date,
                    "end": end_date
                }
            )

        return {"message": f"{doc_type} uploaded (stable schema applied)"}

    except Exception as e:
        return {"error": str(e)}


# =========================
# 📊 DASHBOARD
# =========================
@app.get("/api/dashboard")
def dashboard():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT amount FROM financial_data"))
            rows = result.fetchall()

        if not rows:
            return {"error": "No data"}

        amounts = [r[0] for r in rows if r[0] is not None]

        revenue = sum(a for a in amounts if a > 0)
        expenses = sum(a for a in amounts if a < 0)

        return {
            "revenue": float(revenue),
            "expenses": float(abs(expenses)),
            "net_profit": float(revenue + expenses),
            "gross_margin": float((revenue + expenses) / revenue) if revenue else 0
        }

    except Exception as e:
        return {"error": str(e)}


# =========================
# 📁 FILE LIST
# =========================
@app.get("/api/files")
def get_files():
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM uploaded_files ORDER BY uploaded_at DESC")
            )
            rows = result.fetchall()

        return {"data": [dict(r._mapping) for r in rows]}

    except Exception as e:
        return {"error": str(e)}


# =========================
# 📅 COVERAGE
# =========================
@app.get("/api/coverage")
def coverage():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DISTINCT date FROM financial_data"))
            rows = result.fetchall()

        if not rows:
            return {"data": []}

        existing = {r[0].strftime("%Y-%m-%d") for r in rows}
        full = pd.date_range("2024-01-01", "2024-12-31")

        return {
            "data": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "exists": d.strftime("%Y-%m-%d") in existing
                }
                for d in full
            ]
        }

    except Exception as e:
        return {"error": str(e)}