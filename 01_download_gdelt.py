import os
import gdelt
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def download_daily_gdelt():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 01: Downloading Latest GDELT Data...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    file_date_str = datetime.now().strftime('%Y_%m_%d')
    csv_filename = os.path.join(DATA_DIR, f"gdelt_gkg_GLOBAL_{file_date_str}.csv")
    
    # --- PRE-FLIGHT CLEANUP (THE BLOAT FIX) ---
    print("Connecting to database for pre-flight cleanup...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("🧹 Emptying the trash: Deleting old raw articles...")
        cursor.execute("DELETE FROM article_corpus")            # Wipes the whole table
        cursor.execute("DELETE FROM daily_headline_scores")     # Wipes the whole table
        conn.commit()
        
        print("🗜️ Compacting database to save space (VACUUM)...")
        cursor.execute("VACUUM")
        conn.close()
        print("✅ Database cleanup complete.")
    except Exception as e:
        print(f"⚠️ Could not clean database (it might not exist yet): {e}")
    # ------------------------------------------

    print(f"\nConnecting to GDELT and fetching GKG table for {today_str}...")
    gd2 = gdelt.gdelt(version=2)
    
    try:
        # We enforce English-only stream just like the backfill script
        results = gd2.Search(today_str, table='gkg', coverage=True, translation=False)
        results.to_csv(csv_filename, index=False)
        print(f"✅ Success! Saved today's GDELT data to: {os.path.basename(csv_filename)}")
    except Exception as e:
        print(f"❌ Error downloading today's data: {e}")
        print("It is possible today's global file hasn't been published yet.")

if __name__ == '__main__':
    download_daily_gdelt()
