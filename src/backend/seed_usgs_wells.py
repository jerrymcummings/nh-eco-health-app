import os
import sqlite3
import pandas as pd

def seed_usgs_table():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(backend_dir, "eco_health.db")
    
    print(f"🚀 Connecting to SQLite at: {db_path}")
    
    # CRITICAL: Ensure every row dictionary contains the Latitude and Longitude keys!
    well_data = [
        # --- NEW HAMPSHIRE ---
        {"Site_ID": "USGS-431540071452801", "Site_Name": "NH-WCW 1 Warner", "State": "NH", "County": "Merrimack", "Aquifer_Type": "Sand and gravel", "Depth_To_Water_BMSL_Ft": 1.45, "Status": "Normal", "Latitude": 43.281, "Longitude": -71.816, "Last_Observed": "2026-09-13T08:00:00Z"},
        {"Site_ID": "USGS-430928071474401", "Site_Name": "NH-HMW 1 Hooksett", "State": "NH", "County": "Merrimack", "Aquifer_Type": "Bedrock (Crystalline)", "Depth_To_Water_BMSL_Ft": 12.80, "Status": "Normal", "Latitude": 43.158, "Longitude": -71.462, "Last_Observed": "2026-09-13T08:15:00Z"},
        {"Site_ID": "USGS-425803071104101", "Site_Name": "NH-CVW 1 Nashua", "State": "NH", "County": "Hillsborough", "Aquifer_Type": "Sand and gravel", "Depth_To_Water_BMSL_Ft": 4.12, "Status": "Low / Mild Drought", "Latitude": 42.759, "Longitude": -71.464, "Last_Observed": "2026-09-13T07:45:00Z"},
        {"Site_ID": "USGS-430153070570301", "Site_Name": "NH-FOW 1 Greenfield", "State": "NH", "County": "Hillsborough", "Aquifer_Type": "Glacial Drift", "Depth_To_Water_BMSL_Ft": 8.34, "Status": "Normal", "Latitude": 42.954, "Longitude": -71.874, "Last_Observed": "2026-09-13T06:00:00Z"},
        {"Site_ID": "USGS-432244070544501", "Site_Name": "NH-OWW 1 Ossipee", "State": "NH", "County": "Carroll", "Aquifer_Type": "Sand and gravel", "Depth_To_Water_BMSL_Ft": 5.92, "Status": "Normal", "Latitude": 43.685, "Longitude": -71.116, "Last_Observed": "2026-09-13T08:30:00Z"},
        {"Site_ID": "USGS-442431071465201", "Site_Name": "NH-LCW 1 Lancaster", "State": "NH", "County": "Coos", "Aquifer_Type": "Till / Bedrock", "Depth_To_Water_BMSL_Ft": 22.10, "Status": "Normal", "Latitude": 44.484, "Longitude": -71.573, "Last_Observed": "2026-09-12T23:00:00Z"},
        {"Site_ID": "USGS-430501070502201", "Site_Name": "NH-NWW 1 Newfields", "State": "NH", "County": "Rockingham", "Aquifer_Type": "Bedrock (Crystalline)", "Depth_To_Water_BMSL_Ft": 18.65, "Status": "Critical Low", "Latitude": 43.036, "Longitude": -70.939, "Last_Observed": "2026-09-13T09:00:00Z"},
        
        # --- MAINE ---
        {"Site_ID": "USGS-442116069411201", "Site_Name": "ME-AMW 1 Augusta", "State": "ME", "County": "Kennebec", "Aquifer_Type": "Sand and gravel", "Depth_To_Water_BMSL_Ft": 3.88, "Status": "Normal", "Latitude": 44.310, "Longitude": -69.779, "Last_Observed": "2026-09-13T08:00:00Z"},
        {"Site_ID": "USGS-435102070291901", "Site_Name": "ME-BMW 1 Berwick", "State": "ME", "County": "York", "Aquifer_Type": "Bedrock (Crystalline)", "Depth_To_Water_BMSL_Ft": 14.30, "Status": "Low / Mild Drought", "Latitude": 43.266, "Longitude": -70.865, "Last_Observed": "2026-09-13T07:15:00Z"},
        {"Site_ID": "USGS-445312068450101", "Site_Name": "ME-CMW 1 Calais", "State": "ME", "County": "Washington", "Aquifer_Type": "Glacial Till", "Depth_To_Water_BMSL_Ft": 9.15, "Status": "Normal", "Latitude": 45.189, "Longitude": -67.279, "Last_Observed": "2026-09-13T05:30:00Z"},
        {"Site_ID": "USGS-440211070112401", "Site_Name": "ME-DMW 1 Durham", "State": "ME", "County": "Androscoggin", "Aquifer_Type": "Sand and gravel", "Depth_To_Water_BMSL_Ft": 2.11, "Status": "Normal", "Latitude": 43.975, "Longitude": -70.125, "Last_Observed": "2026-09-13T08:00:00Z"},
        {"Site_ID": "USGS-464105067571201", "Site_Name": "ME-EMW 1 Fort Kent", "State": "ME", "County": "Aroostook", "Aquifer_Type": "Carbonate-Rock", "Depth_To_Water_BMSL_Ft": 7.40, "Status": "Normal", "Latitude": 47.258, "Longitude": -67.931, "Last_Observed": "2026-09-13T04:00:00Z"}
    ]

    
    df = pd.DataFrame(well_data)
    
    conn = sqlite3.connect(db_path)
    try:
        # This replaces the old table design with the new 9-column design
        df.to_sql("usgs_groundwater_wells", conn, if_exists="replace", index=False)
        print("✅ Database successfully expanded!")
        print("📊 Created table: 'usgs_groundwater_wells'")
        print(f"🌲 Inserted {len(df)} monitoring wells spanning NH and ME with coordinate tracking.")
    except Exception as e:
        print(f"❌ Migration Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_usgs_table()

