from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os

app = FastAPI()

# ✅ CORS (allow your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Database
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


@app.get("/")
def root():
    return {"message": "OpenFintel API is running 🚀"}


# 📤 UPLOAD + DATE MERGE
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    df = pd.read_csv(file.file)

    # Normalize
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.fillna("")

    start_date = df["Date"].min()
    end_date = df["Date"].max()

    data = df.to_dict(orient="records")

    with engine.begin() as conn:
        # 🔥 CORE: remove overlapping dates
        conn.execute(
            text("""
                DELETE FROM financial_data
                WHERE date BETWEEN :start AND :end
                AND doc_type = :doc_type
            """),
            {"start": start_date, "end": end_date, "doc_type": doc_type}
        )

        # Insert new rows
        for row in data:
            conn.execute(
                text("""
                    INSERT INTO financial_data (date, description, category, amount, doc_type)
                    VALUES (:date, :desc, :cat, :amt, :doc)
                """),
                {
                    "date": row["Date"],
                    "desc": row.get("Description", ""),
                    "cat": row.get("Category", ""),
                    "amt": float(row.get("Amount", 0)),
                    "doc": doc_type
                }
            )

        # Track file
        conn.execute(
            text("""
                INSERT INTO uploaded_files (file_name, doc_type, start_date, end_date)
                VALUES (:name, :doc, :start, :end)
            """),
            {
                "name": file.filename,
                "doc": doc_type,
                "start": start_date,
                "end": end_date
            }
        )

    return {"message": f"{doc_type} uploaded successfully with merge logic"}


# 📊 DASHBOARD (FIXED)
@app.get("/api/dashboard")
def dashboard():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT date, description, category, amount
                FROM financial_data
            """))
            rows = result.fetchall()

        if not rows:
            return {"error": "No data"}

        # ✅ Safe conversion
        data = []
        for r in rows:
            row = dict(r._mapping)
            if row.get("amount") is None:
                continue
            data.append(row)

        df = pd.DataFrame(data)

        if df.empty:
            return {"error": "No valid data"}

        # Ensure numeric
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["amount"])

        revenue = df[df["amount"] > 0]["amount"].sum()
        expenses = df[df["amount"] < 0]["amount"].sum()

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
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM uploaded_files ORDER BY uploaded_at DESC")
        )
        rows = result.fetchall()

    return {"data": [dict(r._mapping) for r in rows]}


# 📅 COVERAGE TRACKER
@app.get("/api/coverage")
def coverage():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT date FROM financial_data"))
        rows = result.fetchall()

    if not rows:
        return {"data": []}

    existing_dates = {r[0].strftime("%Y-%m-%d") for r in rows}

    full_range = pd.date_range("2024-01-01", "2024-12-31")

    coverage_data = []
    for d in full_range:
        coverage_data.append({
            "date": d.strftime("%Y-%m-%d"),
            "exists": d.strftime("%Y-%m-%d") in existing_dates
        })

    return {"data": coverage_data}