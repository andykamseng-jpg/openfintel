from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ DB
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


# 🏠 ROOT
@app.get("/")
def root():
    return {"message": "OpenFintel API is running 🚀"}


# 📤 UPLOAD (FINAL FIXED VERSION)
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    try:
        df = pd.read_csv(file.file)

        # ✅ CLEAN DATA PROPERLY
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

        # 🔥 remove bad rows (THIS FIXES YOUR ERROR)
        df = df.dropna(subset=["Date", "Amount"])

        # optional fields
        df["Description"] = df.get("Description", "").fillna("")
        df["Category"] = df.get("Category", "").fillna("")

        start_date = df["Date"].min()
        end_date = df["Date"].max()

        records = df.to_dict(orient="records")

        with engine.begin() as conn:
            for row in records:
                conn.execute(
                    text("""
                        INSERT INTO financial_data
                        (date, description, category, amount, doc_type)
                        VALUES (:date, :desc, :cat, :amt, :doc)
                        ON CONFLICT (date, description, doc_type)
                        DO UPDATE SET
                            category = EXCLUDED.category,
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

            # track upload
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

        return {"message": f"{doc_type} uploaded with upsert logic"}

    except Exception as e:
        return {"error": str(e)}


# 📊 DASHBOARD
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


# 📁 FILE LIST
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


# 📅 COVERAGE
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