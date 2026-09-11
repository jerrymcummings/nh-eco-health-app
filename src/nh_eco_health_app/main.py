import os
import re
import sqlite3

from fastapi import FastAPI, HTTPException
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


app = FastAPI(title="NH Eco-Health AI Data Service", version="1.0.0")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "eco_health.db")


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


def execute_sqlite_query(query: str):
    """Execute one read-only SELECT statement against the local database."""
    normalized_query = query.strip()
    if not re.match(r"^SELECT\b", normalized_query, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail="The generated query must be a SELECT statement.",
        )
    if ";" in normalized_query.rstrip(";"):
        raise HTTPException(
            status_code=400,
            detail="Multiple SQL statements are not allowed.",
        )

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failure: {exc}",
        ) from exc

    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(normalized_query).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=f"SQL execution failure: {exc}") from exc
    finally:
        conn.close()


@app.post("/api/query")
def generate_and_execute_query(request: QueryRequest):
    """Generate and execute a read-only SQL query for the user's question."""
    # TODO(testing): Add API tests for validation, SQL rejection, provider failures, and success responses.
    # TODO(security): Add authentication and rate limiting before exposing this beyond localhost.
    # TODO(security): Restrict generated queries to an approved table and column allowlist.
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API Key configuration missing on server.",
        )

    try:
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        db_schema = db.get_table_info()
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        system_instructions = f"""
You are a strict SQLite data analyst.
Translate the user's question into one clean, syntactically correct SQLite SELECT query.

Database Schema Context:
{db_schema}

RULES:
1. Output only one raw SQL SELECT query. Do not use markdown code fences.
2. Only pull columns that exist in the schema.
3. Do not modify the database.

User Question: {request.prompt}
SQL Query:
"""

        ai_response = llm.invoke(system_instructions)
        generated_sql = str(ai_response.content).strip()
        data_records = execute_sqlite_query(generated_sql)

        return {
            "status": "success",
            "sql_executed": generated_sql,
            "data": data_records,
        }
    except HTTPException:
        raise
    except Exception as exc:
        # TODO(operations): Log the exception server-side and hide its details in production.
        raise HTTPException(status_code=502, detail=f"AI data engine failure: {exc}") from exc
