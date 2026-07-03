import os
import sqlite3
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
RETENTION_DAYS = 30

def cleanup_database():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 12: Database Retention & Optimization...")
    
    if not os.path.exists(DB_PATH):
        print("⚠️ Database not found. Skipping cleanup.")
        return

    # 1. Calculate file size before cleanup
    size_before_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"📦 Database size before cleanup: {size_before_mb:.2f} MB")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Establish the 30-day cutoff
    cutoff_date = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime('%Y-%m-%d')
    print(f"🧹 Purging all records older than: {cutoff_date}...")

    # 3. Purge old data from the heavy tables
    tables_to_clean = [
        "article_corpus",
        "daily_headline_scores",
        "daily_cluster_tfidf",
        "daily_ai_enrichment",
        "daily_ai_clusters"
    ]

    for table in tables_to_clean:
        try:
            # Safe check to make sure the table exists before trying to delete
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table} WHERE date < ?", (cutoff_date,))
                deleted_rows = cursor.rowcount
                print(f"  - Cleared {deleted_rows} old rows from {table}.")
        except sqlite3.Error as e:
            print(f"  ⚠️ Error cleaning {table}: {e}")

    conn.commit()

    # 4. The Critical Step: Compress the file
    print("🗜️ Running VACUUM to compress the database (this may take a minute)...")
    start_vacuum = time.time()
    cursor.execute("VACUUM")
    conn.close()
    
    vacuum_time = time.time() - start_vacuum
    print(f"✅ VACUUM complete in {vacuum_time:.2f} seconds.")

    # 5. Calculate file size after cleanup
    size_after_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    saved_mb = size_before_mb - size_after_mb
    
    print(f"📦 Database size after cleanup: {size_after_mb:.2f} MB")
    print(f"📉 Total space reclaimed: {saved_mb:.2f} MB")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 12 Complete.")

if __name__ == '__main__':
    cleanup_database()