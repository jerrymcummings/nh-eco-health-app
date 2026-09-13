
# uv run python src/backend/seed_usgs_wells.py

import os
import re
import sqlite3

from fastapi import FastAPI, HTTPException
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# This module is the backend API. It turns a natural-language question into a
# safe, read-only database query and returns the resulting rows as JSON.
app = FastAPI(title="NH Eco-Health AI Data Service", version="1.0.0")

# Resolve the database beside this package so the app works regardless of the
# directory from which Uvicorn is started.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "eco_health.db")


class QueryRequest(BaseModel):
    # Pydantic validates the request body before the endpoint runs. This rejects
    # empty prompts and limits how much text is sent to the model.
    prompt: str = Field(min_length=1, max_length=2000)


@app.get("/health")
async def health_check():
    # Monitoring can use this without calling the model or opening the database.
    return {"status": "ok"}


def execute_sqlite_query(query: str):
    """Execute one read-only SELECT statement against the local database."""
    # The model produced this SQL, so validate its shape before giving it to
    # SQLite. This is a basic guardrail, not a complete SQL security policy.
    normalized_query = query.strip()
    if not re.match(r"^SELECT\b", normalized_query, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail="The generated query must be a SELECT statement.",
        )
    if ";" in normalized_query.rstrip(";"):
        # Allow one optional trailing semicolon, but reject multiple statements.
        raise HTTPException(
            status_code=400,
            detail="Multiple SQL statements are not allowed.",
        )

    try:
        # mode=ro asks SQLite to open the file read-only. The URI form is needed
        # so SQLite interprets that mode flag instead of treating it as a path.
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failure: {exc}",
        ) from exc

    conn.row_factory = sqlite3.Row
    try:
        # Row objects preserve column names; dicts can be serialized directly by
        # FastAPI as JSON objects.
        rows = conn.execute(normalized_query).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=f"SQL execution failure: {exc}") from exc
    finally:
        # Release the file handle even when SQLite reports invalid SQL.
        conn.close()


@app.post("/api/query")
async def generate_and_execute_query(request: QueryRequest):
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI API Key configuration missing on server.")

    try:
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        db_schema = db.get_table_info()
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # --- PHASE 1: Text-to-SQL Conversion ---
        sql_generation_prompt = f"""
        You are a strict, expert SQLite data analyst. 
        Translate the user's question into a clean, syntactically correct SQLite query.
        
        Database Schema Context:
        {db_schema}
        
        RULES:
        1. Output ONLY the raw SQL query. Do NOT wrap it in markdown code blocks.
        2. Only pull columns that exist in the schema.
        3. CRITICAL: If your query accesses the 'usgs_groundwater_wells' table, you MUST always include the 'Latitude', 'Longitude', and 'Last_Observed' columns in your SELECT statement, even if the user does not explicitly ask for them.
        
        User Question: {request.prompt}
        SQL Query:
        """
        
        ai_sql_response = llm.invoke(sql_generation_prompt)
        generated_sql = ai_sql_response.content.strip()
        
        # Execute the query against your local SQLite instance
        data_records = execute_sqlite_query(generated_sql)
        
        # --- PHASE 2: Conversational Interpretation Synthesis ---
        summary_prompt = f"""
        You are a helpful, expert environmental and public health data analyst. 
        Review the following raw dataset extracted from the database and write a concise, conversational 2-3 sentence summary explaining the findings to the user.
        
        User's Original Question: {request.prompt}
        SQL Query Used: {generated_sql}
        Retrieved Data Rows: {data_records}
        
        Provide a smart summary highlighting any anomalies, patterns, or key counts. Keep it professional yet direct.
        Summary Response:
        """
        
        # If no records were found, pass a simpler instruction
        if not data_records:
            summary_text = "No records matching your specific criteria were found in the local database."
        else:
            ai_summary_response = llm.invoke(summary_prompt)
            summary_text = ai_summary_response.content.strip()
        
        # --- PHASE 3: Return Expanded Payload ---
        return {
            "status": "success",
            "sql_executed": generated_sql,
            "data": data_records,
            "ai_interpretation": summary_text  # Added new key
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Data Engine Exception: {str(e)}")
