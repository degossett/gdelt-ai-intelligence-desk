import os
import sqlite3
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gdelt_Data", "gdelt_brain.db")

def cleanup_database():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 12: Database Surgery & Optimization...")
    
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Database not found at {DB_PATH}. Skipping cleanup.")
        return

    size_before_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"📦 Database size before cleanup: {size_before_mb:.2f} MB")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. NUKE THE DAILY SCRATCHPADS (0 Days Retention) ---
    print("\n🗑️ Emptying daily scratchpad tables...")
    scratchpad_tables = [
        "article_corpus",
        "daily_cluster_tfidf",
        "daily_headline_scores",
        "daily_ai_enrichment"
    ]
    
    for table in scratchpad_tables:
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table}")
                print(f"  - 100% Emptied {table}.")
        except sqlite3.Error as e:
            print(f"  ⚠️ Error emptying {table}: {e}")

    # --- 2. TRIM THE HEAVY CLUSTER MEMORY (7 Days Retention) ---
    cutoff_7_days = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    print(f"\n🧹 Purging short-term memory older than 7 days ({cutoff_7_days})...")
    
    memory_tables_7d = [
        "cluster_word_memory",
        "daily_cluster_counts",
        "daily_ai_clusters"
    ]

    for table in memory_tables_7d:
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table} WHERE date < ?", (cutoff_7_days,))
                print(f"  - Cleared {cursor.rowcount:,} old rows from {table}.")
        except sqlite3.Error as e:
            print(f"  ⚠️ Error cleaning {table}: {e}")

    conn.commit()

    # --- 3. THE COMPRESSION ---
    print("\n🗜️ Running VACUUM to compress the database (this will take a few minutes)...")
    start_vacuum = time.time()
    cursor.execute("VACUUM")
    conn.close()
    
    vacuum_time = time.time() - start_vacuum
    print(f"✅ VACUUM complete in {vacuum_time:.2f} seconds.")

    size_after_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    saved_mb = size_before_mb - size_after_mb
    
    print(f"\n📦 Database size after cleanup: {size_after_mb:.2f} MB")
    print(f"📉 Total space reclaimed: {saved_mb:.2f} MB")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 12 Complete.")

if __name__ == '__main__':
    cleanup_database()