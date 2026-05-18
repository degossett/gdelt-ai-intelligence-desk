import os
import sqlite3
import re
import math
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def get_stopwords(cursor):
    try:
        cursor.execute("SELECT word FROM custom_stopwords")
        return set(row[0] for row in cursor.fetchall())
    except sqlite3.OperationalError:
        return set()

def clean_text(text, stop_words):
    if not text: return set()
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    clean_words = [w for w in words if w not in stop_words and len(w) > 3]
    return set(clean_words)

def process_headline_scores():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 07: Scoring Individual Headlines...")
    print(">>> [VERIFIED] SYNDICATION DEDUPLICATION ACTIVE")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stop_words = get_stopwords(cursor)

    cursor.execute('DROP TABLE IF EXISTS daily_headline_scores')
    cursor.execute('CREATE TABLE daily_headline_scores (date TEXT, cluster_name TEXT, gkg_record_id TEXT, article_url TEXT, headline TEXT, anomaly_score REAL)')

    cursor.execute('SELECT cluster_name, word, tfidf_score FROM daily_cluster_tfidf WHERE date = ?', (today_str,))
    cluster_word_scores = defaultdict(lambda: defaultdict(float))
    for cluster, word, score in cursor.fetchall():
        cluster_word_scores[cluster][word] = score

    cursor.execute('SELECT gkg_record_id, article_url, cluster_tags, persons, organizations, locations, headline FROM article_corpus WHERE date = ?', (today_str,))
    headline_records = []
    
    # --- TRICK 3: THE SYNDICATION KILLER ---
    seen_fingerprints = set()

    for gkg_id, url, tags_str, p_str, o_str, locs_str, headline in cursor.fetchall():
        # 1. Chop off publisher names typically found after a pipe or dash
        raw_core_headline = headline.split('|')[0].split(' - ')[0].strip()
        
        # 2. Extract the first 6 raw words to create a fingerprint
        fingerprint_words = re.sub(r'[^a-z0-9\s]', '', raw_core_headline.lower()).split()
        fingerprint = " ".join(fingerprint_words[:6])
        
        # 3. If we've seen this exact fingerprint today, skip the article!
        if not fingerprint or fingerprint in seen_fingerprints:
            continue
        
        seen_fingerprints.add(fingerprint)
        
        # Now proceed with the normal scoring logic...
        words_in_headline = clean_text(headline, stop_words)
        num_words = len(words_in_headline)
        
        if num_words < 4: 
            continue
            
        clusters = []
        if tags_str: 
            themes = [t for t in tags_str.split(';') if t and not t.startswith('TAX_WORLDLANGUAGES_')]
            clusters.extend(themes)
        if p_str: clusters.extend(["PERSON_" + p for p in p_str.split(';') if p])
        if o_str: clusters.extend(["ORG_" + o for o in o_str.split(';') if o])
        if locs_str:
            for loc in locs_str.split(';'):
                if loc and '#' in loc:
                    country = loc.split('#')[1].split(',')[-1].strip()
                    if country: clusters.append("COUNTRY_" + country)
            
        clean_clusters = set([c.split(',')[0] for c in clusters if c])

        for cluster in clean_clusters:
            raw_headline_score = 0.0
            for word in words_in_headline:
                raw_headline_score += cluster_word_scores[cluster].get(word, 0.0)
            
            normalized_score = raw_headline_score / num_words
            
            if normalized_score > 0:
                headline_records.append((today_str, cluster, gkg_id, url, headline, normalized_score))

    cursor.executemany('INSERT INTO daily_headline_scores VALUES (?, ?, ?, ?, ?, ?)', headline_records)
    conn.commit()
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Kept {len(seen_fingerprints)} unique stories.")

if __name__ == '__main__':
    process_headline_scores()
