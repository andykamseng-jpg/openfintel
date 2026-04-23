from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime

app = FastAPI()

# CORS (allow your Vercel frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


@app.get("/")
def root():
    return {"message": "OpenFintel API is running 🚀"}


# 📤 UPLOAD + DATE MERGE LOGIC
@app.post("/api/upload")
async def upload(file: UploadFile, doc_type: str = Form(...)):
    df = pd.read_csv(file.file)

    df["Date"] = pd.to_datetime(df["Date"])

    start_date = df["Date"].min()
    end_date = df["Date"].max()

    data = df.to_dict(orient="records")

    with engine.begin() as conn:
        # 🔥 DELETE overlapping data (core logic)
        conn.execute(
            text("""
                DELETE FROM financial_data
                WHERE date BETWEEN :start AND :end
                AND doc_type = :doc_type
            """),
            {"start": start_date, "end": end_date, "doc_type": doc_type}
        )

        # INSERT new data
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
                    "amt": row.get("Amount", 0),
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

    return {"message": f"{doc_type} uploaded with merge logic"}


# 📊 DASHBOARD
@app.get("/api/dashboard")
def dashboard():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM financial_data")).fetchall()

    if not rows:
        return {"error": "No data"}

    df = pd.DataFrame(rows, columns=rows[0].keys())

    revenue = df[df["amount"] > 0]["amount"].sum()
    expenses = df[df["amount"] < 0]["amount"].sum()

    return {
        "revenue": float(revenue),
        "expenses": float(abs(expenses)),
        "net_profit": float(revenue + expenses),
        "gross_margin": float((revenue + expenses) / revenue) if revenue else 0
    }


# 📁 FILE LIST
@app.get("/api/files")
def files():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM uploaded_files ORDER BY uploaded_at DESC")).fetchall()

    return {"data": [dict(row._mapping) for row in rows]}


# 📅 COVERAGE
@app.get("/api/coverage")
def coverage():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT date FROM financial_data")).fetchall()

    dates = {r[0].strftime("%Y-%m-%d") for r in rows}

    full_year = pd.date_range("2024-01-01", "2024-12-31")

    result = []
    for d in full_year:
        result.append({
            "date": d.strftime("%Y-%m-%d"),
            "exists": d.strftime("%Y-%m-%d") in dates
        })

    return {"data": result}