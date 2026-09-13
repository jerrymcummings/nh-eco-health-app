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
def generate_and_execute_query(request: QueryRequest):
    """Generate and execute a read-only SQL query for the user's question."""
    # TODO(testing): Add API tests for validation, SQL rejection, provider failures, and success responses.
    # TODO(security): Add authentication and rate limiting before exposing this beyond localhost.
    # TODO(security): Restrict generated queries to an approved table and column allowlist.
    if not os.environ.get("OPENAI_API_KEY"):
        # Fail early with a clear configuration error instead of making a model
        # call that cannot succeed.
        raise HTTPException(
            status_code=500,
            detail="OpenAI API Key configuration missing on server.",
        )

    try:
        # Read the schema so the model can reference real tables and columns.
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        db_schema = db.get_table_info()
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # This prompt is the contract with the model: return one SELECT statement
        # and no explanatory markdown.
        system_instructions = f"""
        You are a strict, expert SQLite data analyst. 
        Translate the user's question into a clean, syntactically correct SQLite query.
        
        Database Schema Context:
        {db_schema}
        
        RULES:
        1. Output ONLY the raw SQL query. Do NOT wrap it in markdown code blocks like ```sql.
        2. Only pull columns that exist in the schema.
        3. CRITICAL: If your query accesses the 'usgs_groundwater_wells' table, you MUST always include the 'Latitude' and 'Longitude' columns in your SELECT statement, even if the user does not explicitly mention them.
        
        User Question: {request.prompt}
        SQL Query:
        """


        ai_response = llm.invoke(system_instructions)
        # The message object's content is the model's text. Strip whitespace
        # before passing it to the SQL guard.
        generated_sql = str(ai_response.content).strip()
        data_records = execute_sqlite_query(generated_sql)

        # Returning SQL as well as rows keeps the response inspectable during
        # development and hides LangChain objects from the frontend contract.
        return {
            "status": "success",
            "sql_executed": generated_sql,
            "data": data_records,
        }
    except HTTPException:
        # Preserve deliberate errors from validation and database code.
        raise
    except Exception as exc:
        # TODO(operations): Log the exception server-side and hide its details in production.
        raise HTTPException(status_code=502, detail=f"AI data engine failure: {exc}") from exc
