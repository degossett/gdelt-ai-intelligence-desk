import os
import sqlite3
import re
import math
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
        return set()

def clean_text(text, stop_words):
    if not text: return set()
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    return set([w for w in words if w not in stop_words and len(w) > 3])

def calculate_daily_tfidf():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 06: Calculating Daily TF-IDF...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stop_words = get_stopwords(cursor)

    cursor.execute('DROP TABLE IF EXISTS daily_cluster_tfidf')
    cursor.execute('''CREATE TABLE daily_cluster_tfidf
                      (date TEXT, cluster_name TEXT, word TEXT, daily_tf REAL, rolling_idf REAL, tfidf_score REAL)''')

    cursor.execute("SELECT cluster_name FROM cluster_status WHERE status = 'ACTIVE'")
    active_clusters = set(row[0] for row in cursor.fetchall())

    cursor.execute('SELECT cluster_tags, persons, organizations, locations, headline FROM article_corpus WHERE date = ?', (today_str,))
    cluster_term_counts = defaultdict(lambda: defaultdict(int))

    for tags_str, p_str, o_str, locs_str, headline in cursor.fetchall():
        words = clean_text(headline, stop_words)
        if not words: continue

        clusters = []
        if tags_str: clusters.extend([t for t in tags_str.split(';') if t and not t.startswith('TAX_WORLDLANGUAGES_')])
        if p_str: clusters.extend(["PERSON_" + p for p in p_str.split(';') if p])
        if o_str: clusters.extend(["ORG_" + o for o in o_str.split(';') if o])
        if locs_str:
            for loc in locs_str.split(';'):
                if loc and '#' in loc:
                    country = loc.split('#')[1].split(',')[-1].strip()
                    if country: clusters.append("COUNTRY_" + country)

        clean_clusters = set([c.split(',')[0] for c in clusters if c])

        for cluster in clean_clusters:
            if cluster in active_clusters:
                for word in words:
                    cluster_term_counts[cluster][word] += 1

    rolling_idfs = defaultdict(dict)
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='rolling_cluster_idf' OR name='rolling_idf' OR name='cluster_idf')")
        table_match = cursor.fetchone()
        if table_match:
            table_name = table_match[0]
            cursor.execute(f'SELECT cluster_name, word, idf_score FROM {table_name}')
            for c_name, w, idf in cursor.fetchall():
                rolling_idfs[c_name][w] = idf
    except Exception as e:
        pass

    insert_data = []
    for cluster, words_dict in cluster_term_counts.items():
        for word, raw_tf in words_dict.items():
            log_tf = 1.0 + math.log10(raw_tf)
            idf = rolling_idfs[cluster].get(word, 1.5) 
            tfidf_score = log_tf * idf
            insert_data.append((today_str, cluster, word, log_tf, idf, tfidf_score))

    cursor.executemany('INSERT INTO daily_cluster_tfidf VALUES (?, ?, ?, ?, ?, ?)', insert_data)
    conn.commit()
    conn.close()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 06 Complete.")

if __name__ == '__main__':
    calculate_daily_tfidf()