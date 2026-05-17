import os
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = r"C:\Users\schli\OneDrive\Documents\gdelt"
DB_PATH = os.path.join(BASE_DIR, r"gdelt_Data\gdelt_brain.db")

def get_stopwords(cursor):
    try:
        cursor.execute("SELECT word FROM custom_stopwords")
        return set(row[0] for row in cursor.fetchall())
    except sqlite3.OperationalError:
        print("⚠️ Warning: custom_stopwords table not found. Using empty set.")
        return set()

def clean_text(text, stop_words):
    if not text: return ""
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    clean_words = [w for w in words if w not in stop_words and len(w) > 3]
    return " ".join(clean_words)

def process_memory_bank():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 04: Daily Cluster Word Memory...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load dynamic stopwords from database
    stop_words = get_stopwords(cursor)
    print(f">>> [VERIFIED] USING {len(stop_words)} DYNAMIC STOPWORDS")

    cursor.execute('CREATE TABLE IF NOT EXISTS cluster_word_memory (date TEXT, cluster_name TEXT, word TEXT, docs_with_word INTEGER, total_cluster_docs INTEGER, PRIMARY KEY (date, cluster_name, word))')
    cursor.execute('DELETE FROM cluster_word_memory WHERE date = ?', (today_str,))
    
    cursor.execute("SELECT cluster_name FROM cluster_status WHERE status = 'ACTIVE'")
    active_clusters_set = set(row[0] for row in cursor.fetchall())
    
    cursor.execute('SELECT cluster_tags, persons, organizations, locations, headline FROM article_corpus WHERE date = ?', (today_str,))
    rows = cursor.fetchall()

    cluster_doc_counts = defaultdict(int)
    cluster_term_dfs = defaultdict(lambda: defaultdict(int))

    for tags_str, persons_str, orgs_str, locs_str, headline in rows:
        words = set(clean_text(headline, stop_words).split())
        if not words: continue
            
        clusters = []
        if tags_str: 
            themes = [t for t in tags_str.split(';') if t]
            themes = [t for t in themes if not t.startswith('TAX_WORLDLANGUAGES_')]
            clusters.extend(themes)
        if persons_str: clusters.extend(["PERSON_" + p for p in persons_str.split(';') if p])
        if orgs_str: clusters.extend(["ORG_" + o for o in orgs_str.split(';') if o])
        if locs_str:
            for loc in locs_str.split(';'):
                if loc and '#' in loc:
                    country = loc.split('#')[1].split(',')[-1].strip()
                    if country: clusters.append("COUNTRY_" + country)
            
        clean_clusters = set([c.split(',')[0] for c in clusters if c])

        for cluster in clean_clusters:
            if cluster in active_clusters_set:
                cluster_doc_counts[cluster] += 1
                for word in words:
                    cluster_term_dfs[cluster][word] += 1

    memory_records = []
    for cluster, n_docs in cluster_doc_counts.items():
        for word, df in cluster_term_dfs[cluster].items():
            memory_records.append((today_str, cluster, word, df, n_docs))

    cursor.executemany('INSERT INTO cluster_word_memory VALUES (?, ?, ?, ?, ?)', memory_records)
    conn.commit()
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 04 Complete.")

if __name__ == '__main__':
    process_memory_bank()