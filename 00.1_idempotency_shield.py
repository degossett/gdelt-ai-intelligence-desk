import os
import sqlite3
from datetime import datetime

# This works perfectly on BOTH Windows and Linux automatically!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def surgical_clean():
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"✨ Target Date for Cleanup: {today_str}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Could not find database at {DB_PATH}. Make sure it's in your local gdelt_Data folder!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # The 4 tables that got cross-contaminated today
    tables = [
        'daily_cluster_counts', 
        'cluster_word_memory', 
        'daily_headline_scores', 
        'daily_ai_clusters'
    ]
    
    print("🧹 Commencing surgical strike...")
    for table in tables:
        cursor.execute(f"DELETE FROM {table} WHERE date = ?", (today_str,))
        print(f"  -> Wiped today's polluted rows from: {table}")
        
    conn.commit()
    conn.close()
    print("✅ Success! Today's pollution is gone. Your 30-day history is safe!")

if __name__ == '__main__':
    surgical_clean()
