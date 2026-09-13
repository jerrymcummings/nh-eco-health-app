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
load_dotenv(dotenv_path)

API_URL = os.environ.get("ECO_HEALTH_API_URL", "http://127.0.0")

st.set_page_config(page_title="AI Eco-Health Dashboard", page_icon="🌲", layout="wide")

st.title("🌲 NH Environmental Health AI Copilot (Decoupled Architecture)")

user_prompt = st.text_input(
    "💬 Ask the data anything:",
    value="Show me all wells in New Hampshire where aquifer type is sand and gravel."
)

if user_prompt:
    try:
        with st.spinner("Sending request to FastAPI data engine..."):
            payload = {"prompt": user_prompt}
            response = requests.post(API_URL, json=payload, timeout=30)
    except requests.RequestException as exc:
        st.error(f"Could not reach the FastAPI endpoint at {API_URL}.")
        st.caption(str(exc))
    else:
        if response.status_code == 200:
            try:
                result_json = response.json()
                
                # 🛠️ FRONTEND DIAGNOSTIC READOUT
                st.write("### 🛠️ Frontend Diagnostic Hub")
                st.write(f"Contains 'time_series' key? : `{ 'time_series' in result_json }`")
                if 'time_series' in result_json:
                    st.write(f"Length of time_series data array: `{len(result_json['time_series'])}`")
                
                generated_sql = result_json.get("sql_executed", "N/A")
                raw_records = result_json.get("data", [])

                df_results = pd.DataFrame(raw_records)

                if not df_results.empty:
                    if "Latitude" in df_results.columns and "Longitude" in df_results.columns:
                        df_results["Latitude"] = pd.to_numeric(df_results["Latitude"], errors='coerce')
                        df_results["Longitude"] = pd.to_numeric(df_results["Longitude"], errors='coerce')
                        df_results = df_results.astype({"Latitude": float, "Longitude": float})
            
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📋 Data Telemetry View")
                        st.dataframe(df_results, width="stretch", hide_index=True)
                        
                    with col2:
                        if "Latitude" in df_results.columns and "Longitude" in df_results.columns:
                            st.subheader("🗺️ Hydrological Spatial Map")
                            avg_lat = df_results["Latitude"].mean()
                            avg_lon = df_results["Longitude"].mean()
                            dynamic_zoom = 9.5 if len(df_results) == 1 else 5.5
                            
                            fig_map = px.scatter_map(
                                df_results,
                                lat="Latitude",
                                lon="Longitude",
                                hover_name="Site_Name",
                                hover_data=["Aquifer_Type", "Depth_To_Water_BMSL_Ft", "Last_Observed"],
                                color="Status",
                                color_discrete_map={"Normal": "#2ecc71", "Low / Mild Drought": "#f39c12", "Critical Low": "#e74c3c"},
                                zoom=dynamic_zoom,
                                center={"lat": avg_lat, "lon": avg_lon},
                                title="Active Well Aquifer Status Check"
                            )
                            fig_map.update_layout(map_style="open-street-map", margin={"r":0,"t":40,"l":0,"b":0})
                            st.plotly_chart(fig_map, width="stretch")
                            
                    if "time_series" in result_json and result_json["time_series"]:
                        st.markdown("---")
                        target_station_label = result_json.get("target_station", "Primary Station")
                        st.subheader(f"📈 Chronological Water Levels: {target_station_label}")
                        
                        df_ts = pd.DataFrame(result_json["time_series"])
                        
                        fig_line = px.line(
                            df_ts,
                            x="Observation_Date",
                            y="Depth_Below_Surface_Ft",
                            title="Water Table Trends",
                            markers=True,
                            labels={"Depth_Below_Surface_Ft": "Depth (Feet)", "Observation_Date": "Date"}
                        )
                        fig_line.update_yaxes(autorange="reversed")
                        st.plotly_chart(fig_line, width="stretch")

                    if "ai_interpretation" in result_json:
                        st.markdown("### 🧠 AI Analysis & Insights")
                        st.success(result_json["ai_interpretation"])

                    st.markdown("---")
                    st.markdown("### Query Details")
                    st.metric(label="Data Execution Pipeline Source", value=generated_sql)
                    
                    # Output raw response payload JSON data directly to look inside
                    st.write("#### Raw JSON Output from Backend:")
                    st.json(result_json)
                else:
                    st.warning("API connection succeeded, but query evaluated to zero matches.")
            except (KeyError, TypeError, ValueError) as exc:
                st.error("The FastAPI response could not be rendered.")
                st.caption(str(exc))
        else:
            st.error(f"Backend API Service Error (Status {response.status_code}): {response.text}")
