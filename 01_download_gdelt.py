import os
import gdelt
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def download_daily_gdelt():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 01: Downloading Latest GDELT Data...")
    
    # --- TIME TRAVEL: CALCULATE YESTERDAY'S FULL 24-HOUR CYCLE ---
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    yesterday_file_str = yesterday.strftime('%Y_%m_%d')
    
    csv_filename = os.path.join(DATA_DIR, f"gdelt_gkg_GLOBAL_{yesterday_file_str}.csv")
    
    # --- PRE-FLIGHT CLEANUP (THE BLOAT FIX) ---
    print("Connecting to database for pre-flight cleanup...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("🧹 Emptying the trash: Deleting old raw articles...")
        cursor.execute("DELETE FROM article_corpus")
        cursor.execute("DELETE FROM daily_headline_scores")
        conn.commit()
        
        print("🗜️ Compacting database to save space (VACUUM)...")
        cursor.execute("VACUUM")
        conn.close()
        print("✅ Database cleanup complete.")
    except Exception as e:
        print(f"⚠️ Could not clean database (it might not exist yet): {e}")
    # ------------------------------------------

    print(f"\nConnecting to GDELT and fetching GKG table for {yesterday_str} (Full 24-Hour Cycle)...")
    gd2 = gdelt.gdelt(version=2)
    
    try:
        # We enforce English-only stream just like the backfill script
        results = gd2.Search(yesterday_str, table='gkg', coverage=True, translation=False)
        results.to_csv(csv_filename, index=False)
        print(f"✅ Success! Saved a full 24-hour cycle of global news to: {os.path.basename(csv_filename)}")
    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        print("It is possible GDELT is currently updating its master servers.")

if __name__ == '__main__':
    download_daily_gdelt()
