import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# This file is the user-facing Streamlit client. It does not talk to SQLite or
# OpenAI directly; it sends a question to the separate FastAPI service.
st.set_page_config(page_title="AI Eco-Health Dashboard", page_icon="🌲", layout="wide")

# Keep the frontend endpoint configurable when the API runs on another host or port.
API_URL = os.environ.get("ECO_HEALTH_API_URL", "http://127.0.0.1:8000/api/query")

st.title("🌲 NH Environmental Health AI Copilot (Decoupled Architecture)")
st.markdown(
    """
    This frontend application is completely decoupled. It makes standard structured **REST API requests** 
    to a backend **FastAPI microservice** which handles the AI query compilation and database layers.
    """
)

user_prompt = st.text_input(
    "💬 Ask the data anything:",
    value="Show me the counties with the highest asthma ER rates in 2024, sorted from worst to best."
)

if user_prompt:
    try:
        with st.spinner("Sending request to FastAPI data engine..."):
            # The backend expects a JSON object whose key is named "prompt".
            payload = {"prompt": user_prompt}
            response = requests.post(API_URL, json=payload, timeout=30)
    except requests.RequestException as exc:
        # This covers network-level failures, such as a stopped API or timeout.
        st.error(f"Could not reach the FastAPI endpoint at {API_URL}.")
        st.caption(str(exc))
    else:
        if response.status_code == 200:
            try:
                # A successful response contains generated SQL and database rows.
                # Pandas makes those rows easy to display and plot.
                result_json = response.json()
                generated_sql = result_json["sql_executed"]
                raw_records = result_json["data"]

                df_results = pd.DataFrame(raw_records)

                if not df_results.empty:
                    # Show the same response as both inspectable values and a chart.
                    col1, col2 = st.columns(2)
                
                    with col1:
                        st.subheader("📋 Backend JSON Payload Mapping")
                        st.dataframe(df_results, width="stretch", hide_index=True)
                    
                    with col2:
                        st.subheader("📊 Live Plotly Render")
                        # Prefer numeric fields as measures; Year is normally a
                        # category or filter rather than the value being plotted.
                        numeric_cols = df_results.select_dtypes(include=['number']).columns.tolist()
                        if "Year" in numeric_cols and len(numeric_cols) > 1:
                            numeric_cols.remove("Year")
                        # Use County when available; otherwise use the first column.
                        target_x = "County" if "County" in df_results.columns else df_results.columns[0]
                        chart_columns = [column for column in df_results.columns if column != target_x]
                        target_y = numeric_cols or chart_columns[:1]

                        if target_y:
                            # Plotly accepts several y columns, so multiple measures
                            # returned by one query can be compared in one chart.
                            fig = px.bar(
                                df_results,
                                x=target_x,
                                y=target_y,
                                title=f"API Data Rendered: {str(target_y).replace('_', ' ')}",
                                color=target_x,
                            )
                            st.plotly_chart(fig, width="stretch")
                        else:
                            st.info("The response contains no separate measure to chart.")
                    
                    # Show the generated query while this local tool is being developed.
                    # TODO(privacy): Hide raw SQL and backend details in a production UI.
                    st.markdown("---")
                    st.markdown("### Query Details")
                    st.info("✅ HTTP Status 200 OK received from upstream service.")
                    st.write("SQL script compiled and executed remotely by FastAPI:")
                    st.code(generated_sql, language="sql")
                else:
                    st.warning("API connection succeeded, but query evaluated to zero matches.")
            except (KeyError, TypeError, ValueError) as exc:
                # HTTP 200 does not guarantee the JSON has the shape this UI needs.
                st.error("The FastAPI response could not be rendered.")
                st.caption(str(exc))
        else:
            # The API was reachable, but rejected or failed the request.
            st.error(f"Backend API Service Error (Status {response.status_code}): {response.text}")
