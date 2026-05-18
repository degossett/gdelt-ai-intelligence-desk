import os
import sqlite3
import math
from datetime import datetime

# --- CONFIGURATION ---
# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

# --- PRUNING THRESHOLDS ---
MIN_DF = 2           # Word must appear in at least 2 docs over 30 days
MAX_DF_RATIO = 0.80  # Drop words appearing in > 80% of cluster's docs

def process_rolling_idf():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 05: Rolling 30-Day IDF Math...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the finalized IDF table (Notice we drop the Date column, this is a rolling cache)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rolling_30d_idf (
            cluster_name TEXT,
            word TEXT,
            idf_score REAL,
            last_updated TEXT,
            PRIMARY KEY (cluster_name, word)
        )
    ''')
    
    print("Wiping old cache to build fresh 30-day baseline...")
    cursor.execute('DELETE FROM rolling_30d_idf')
    
    # 1. Get N (Total documents per cluster over the last 30 days)
    # We use our daily_cluster_counts table to get the perfect historical cluster volume
    print("Calculating 30-day cluster volume (N)...")
    cursor.execute('''
        SELECT cluster_name, SUM(article_count) 
        FROM daily_cluster_counts 
        WHERE date >= date('now', '-30 days')
        GROUP BY cluster_name
    ''')
    cluster_N = {row[0]: row[1] for row in cursor.fetchall()}

    # 2. Get df (Total documents with the word per cluster over 30 days)
    print("Aggregating 30-day word frequencies (df)... (This may take a minute)")
    cursor.execute('''
        SELECT cluster_name, word, SUM(docs_with_word) 
        FROM cluster_word_memory 
        WHERE date >= date('now', '-30 days')
        GROUP BY cluster_name, word
    ''')
    word_frequencies = cursor.fetchall()

    # 3. Calculate IDF
    print("Calculating math and pruning vocabulary...")
    idf_records = []
    today_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for cluster, word, df in word_frequencies:
        # Get the cluster's N
        N = cluster_N.get(cluster, 0)
        if N == 0:
            continue
        
        # Pruning: Noise and Stopwords
        if df < MIN_DF or (df / N) > MAX_DF_RATIO:
            continue
        
        # The Formula: log(N / df)
        idf_score = math.log(N / df)
        idf_records.append((cluster, word, idf_score, today_str))

    print(f"Generated {len(idf_records)} highly-optimized Rolling IDF scores.")

    print("Inserting rolling IDF scores into database...")
    # Chunksize to protect against variable limits
    cursor.executemany('''
        INSERT INTO rolling_30d_idf (cluster_name, word, idf_score, last_updated)
        VALUES (?, ?, ?, ?)
    ''', idf_records)
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 05 Complete. Baseline locked.")

if __name__ == '__main__':
    process_rolling_idf()
