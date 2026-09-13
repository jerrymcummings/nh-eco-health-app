import os
import sqlite3
import pandas as pd

def migrate_csv_to_sqlite():
    # 1. Resolve exact file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "nh_environmental_health_mock_data.csv")
    db_path = os.path.join(current_dir, "eco_health.db")
    
    print("🚀 Initializing local database migration...")
    
    # 2. Read the CSV data using pandas
    if not os.path.exists(csv_path):
        print(f"❌ Error: Could not find {csv_path}. Please verify the file location.")
        return
        
    df = pd.read_csv(csv_path)
    
    # 3. Open a connection to SQLite (creates the file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    
    # 4. Write dataframe to SQL table
    # This automatically maps columns and infers database data types
    df.to_sql("environmental_health", conn, if_exists="replace", index=False)
    
    print(f"✅ Success! Generated SQLite database at: {db_path}")
    print(f"📊 Loaded {len(df)} rows into the 'environmental_health' table.")
    
    # Close the connection cleanly
    conn.close()

if __name__ == "__main__":
    migrate_csv_to_sqlite()
