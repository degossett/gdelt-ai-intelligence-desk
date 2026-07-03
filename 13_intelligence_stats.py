import os
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def run_stats():
    print(f"\n📊 GDELT INTELLIGENCE DESK - SYSTEM METRICS 📊")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    daily_articles = 0
    final_briefs = 0

    # 1. Today's Ingestion (Article Corpus)
    try:
        cursor.execute("SELECT COUNT(*) FROM article_corpus")
        daily_articles = cursor.fetchone()[0]
        print(f"📰 Total Global Articles Ingested Today:    {daily_articles:,}")
    except Exception: pass

    # 2. Vocabulary Size (Rolling IDF Memory)
    try:
        cursor.execute("SELECT COUNT(DISTINCT word) FROM rolling_30d_idf")
        vocab_size = cursor.fetchone()[0]
        print(f"🧠 Active Vocabulary (30-Day Memory):      {vocab_size:,} unique words")
    except Exception: pass

    # 3. Active Clusters/Themes
    try:
        cursor.execute("SELECT COUNT(DISTINCT cluster_name) FROM cluster_status WHERE status = 'ACTIVE'")
        active_clusters = cursor.fetchone()[0]
        print(f"🌐 Global Themes Actively Tracked:         {active_clusters:,}")
    except Exception: pass

    # 4. Total Math Data Points (TF-IDF matrix size)
    try:
        cursor.execute("SELECT COUNT(*) FROM daily_cluster_tfidf")
        matrix_size = cursor.fetchone()[0]
        print(f"🧮 Daily TF-IDF Matrix Calculations:       {matrix_size:,} data points")
    except Exception: pass

    # 5. Enrichment/Filter Stats
    try:
        cursor.execute("SELECT COUNT(*) FROM daily_ai_enrichment WHERE is_ai_related = 1")
        enriched_articles = cursor.fetchone()[0]
        print(f"🎯 Highly Relevant Articles Isolated:      {enriched_articles:,}")
    except Exception: pass

    # 6. Final Output (Briefs)
    try:
        cursor.execute("SELECT COUNT(*) FROM daily_ai_clusters")
        final_briefs = cursor.fetchone()[0]
        print(f"✅ Final Intelligence Clusters Generated:  {final_briefs:,}")
    except Exception: pass

    # 7. The "Data Engineering" Fun Fact: Compression Ratio
    try:
        if daily_articles > 0 and final_briefs > 0:
            print("-" * 60)
            print("🚀 THE OSINT COMPRESSION METRIC:")
            print(f"Distilled {daily_articles:,} raw global headlines down to {final_briefs} high-signal executive briefs.")
    except Exception: pass

    print("-" * 60)
    conn.close()

if __name__ == '__main__':
    run_stats()
