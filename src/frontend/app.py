import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Go back two folders from 'src/frontend/' to hit the root project folder
current_dir = os.path.dirname(os.path.abspath(__file__))
root_project_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
dotenv_path = os.path.join(root_project_dir, ".env")

# Load variables from the central root configuration file
print(f"🔑 Loading environment variables from: {dotenv_path}")
load_dotenv(dotenv_path)

API_URL = os.environ.get("ECO_HEALTH_API_URL", "http://127.0.0")
print(f"🌐 Using FastAPI endpoint: {API_URL}")

# This file is the user-facing Streamlit client. It does not talk to SQLite or
# OpenAI directly; it sends a question to the separate FastAPI service.
st.set_page_config(page_title="AI Eco-Health Dashboard", page_icon="🌲", layout="wide")

st.title("🌲 NH Environmental Health AI Copilot (Decoupled Architecture)")
st.markdown(
    """
    This frontend application is completely decoupled. It makes standard structured **REST API requests** 
    to a backend **FastAPI microservice** which handles the AI query compilation and database layers.
    """
)

user_prompt = st.text_input(
    "💬 Ask the data anything:",
    value="Show me all wells where aquifer type is sand and gravel."
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
                result_json = response.json()
                generated_sql = result_json["sql_executed"]
                raw_records = result_json["data"]

                df_results = pd.DataFrame(raw_records)

                if not df_results.empty:

                    #  Force conversion directly across all downstream references
                    if "Latitude" in df_results.columns and "Longitude" in df_results.columns:
                        df_results["Latitude"] = pd.to_numeric(df_results["Latitude"], errors='coerce')
                        df_results["Longitude"] = pd.to_numeric(df_results["Longitude"], errors='coerce')
                        
                        # Add these lines to completely eliminate string evaluation traps:
                        df_results = df_results.astype({"Latitude": float, "Longitude": float})
            
                    col1, col2 = st.columns(2)

                    
                    with col1:
                        st.subheader("📋 Data Telemetry View")
                        st.dataframe(df_results, width="stretch", hide_index=True)
                        
                    with col2:
                        # Check if the payload data contains geographic coordinates
                        if "Latitude" in df_results.columns and "Longitude" in df_results.columns:
                            st.subheader("🗺️ Hydrological Spatial Map")
                            
                            # Streamlined Plotly Map engine with explicit New England centering
                            fig_map = px.scatter_map(
                                df_results,
                                lat="Latitude",
                                lon="Longitude",
                                hover_name="Site_Name",
                                hover_data=["Aquifer_Type", "Depth_To_Water_BMSL_Ft"],
                                color="Status",
                                color_discrete_map={
                                    "Normal": "#2ecc71",
                                    "Low / Mild Drought": "#f39c12",
                                    "Critical Low": "#e74c3c"
                                },
                                zoom=6,
                                # ADD THIS PARAMETER: Force center coordinates to Loudon, New Hampshire region
                                center={"lat": 43.286, "lon": -71.463},
                                title="Active Well Aquifer Status Check"
                            )

                            
                            # Style the map to open-source OpenStreetMap base layouts
                            fig_map.update_layout(
                                map_style="open-street-map",
                                margin={"r":0,"t":40,"l":0,"b":0}
                            )
                            st.plotly_chart(fig_map, width="stretch")
                            
                        else:
                            # Fallback plot behavior for non-spatial datasets (like public health metrics)
                            st.subheader("📊 Statistical Analysis Plot")
                            numeric_cols = df_results.select_dtypes(include=['number']).columns.tolist()
                            if "Year" in numeric_cols and len(numeric_cols) > 1:
                                numeric_cols.remove("Year")
                                
                            target_y = numeric_cols if numeric_cols else df_results.columns[-1]
                            target_x = "County" if "County" in df_results.columns else df_results.columns
                            
                            fig = px.bar(
                                df_results,
                                x=target_x,
                                y=target_y,
                                title=f"API Data Rendered: {str(target_y).replace('_', ' ')}",
                                color=target_x if target_x in df_results.columns else None
                            )
                            st.plotly_chart(fig, width="stretch")
                   
                    # Show the generated query details at the bottom
                    st.markdown("---")
                    st.markdown("### Query Details")
                    st.info("✅ HTTP Status 200 OK received from upstream service.")
                    st.write("SQL script compiled and executed remotely by FastAPI:")
                    st.code(generated_sql, language="sql")
                else:
                    st.warning("API connection succeeded, but query evaluated to zero matches.")
            except (KeyError, TypeError, ValueError) as exc:
                st.error("The FastAPI response could not be rendered.")
                st.caption(str(exc))
        else:
            st.error(f"Backend API Service Error (Status {response.status_code}): {response.text}")
