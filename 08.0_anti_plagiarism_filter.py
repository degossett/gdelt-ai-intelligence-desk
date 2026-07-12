import os
import sqlite3
import re
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

def get_fingerprint(text):
    """Extracts 4-letter root prefixes of significant words for fuzzy matching."""
    if not text: return set()
    # Keep alphanumeric, convert to lowercase
    words = re.sub(r'[^a-z0-9]', ' ', text.lower()).split()
    # Keep prefixes of 4 chars for words that are at least 4 chars long (e.g., 'sues' and 'suing' both become 'suin'/'sues' -> wait, 'sues'->'sues', 'suing'->'suin'. Actually, 4-letters catches plurals like 'secret' and 'secrets' perfectly).
    return set(w[:4] for w in words if len(w) >= 4)

def run_anti_plagiarism():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 07.1: Anti-Plagiarism Bouncer...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fetch published topics and summaries from the last 3 days
    try:
        cursor.execute('''
            SELECT topic_name, summary 
            FROM daily_ai_clusters 
            WHERE date >= date(?, '-3 days') AND date < ?
        ''', (today_str, today_str))
        past_clusters = cursor.fetchall()
    except sqlite3.OperationalError:
        print("⚠️ daily_ai_clusters table not found. Skipping filter.")
        conn.close()
        return

    if not past_clusters:
        print("✅ No past clusters found in the last 3 days. Skipping filter.")
        conn.close()
        return

    # 2. Build fingerprints for past stories
    past_fingerprints = []
    for topic, summary in past_clusters:
        combined_text = f"{topic} {summary}"
        past_fingerprints.append(get_fingerprint(combined_text))

    print(f"🧠 Loaded {len(past_fingerprints)} past stories into the Bouncer's memory.")

    # 3. Fetch today's freshly scored headlines
    try:
        cursor.execute('SELECT rowid, headline FROM daily_headline_scores WHERE date = ?', (today_str,))
        today_headlines = cursor.fetchall()
    except sqlite3.OperationalError:
        print("❌ daily_headline_scores table not found. Did Step 07 run?")
        conn.close()
        return

    if not today_headlines:
        print("⚠️ No headlines found for today.")
        conn.close()
        return

    print(f"🔍 Scanning {len(today_headlines)} headlines for syndication lag...")

    # 4. Compare and flag duplicates
    rows_to_delete = []
    for rowid, headline in today_headlines:
        hl_fingerprint = get_fingerprint(headline)
        
        # If the headline is too short to fingerprint, skip it
        if len(hl_fingerprint) < 3:
            continue
            
        for past_fp in past_fingerprints:
            # Calculate how many root words overlap
            overlap = hl_fingerprint.intersection(past_fp)
            
            # If 40% or more of the headline's significant roots match a past story, it's a duplicate
            match_ratio = len(overlap) / len(hl_fingerprint)
            
            if match_ratio >= 0.4 and len(overlap) >= 3:
                rows_to_delete.append((rowid,))
                break # No need to check other past stories, it's a goner

    # 5. Execute the deletions
    if rows_to_delete:
        cursor.executemany('DELETE FROM daily_headline_scores WHERE rowid = ?', rows_to_delete)
        conn.commit()
        print(f"🗑️ Bouncer deleted {len(rows_to_delete)} overlapping headlines before they reached the AI.")
    else:
        print("✅ No overlapping stories found today. The news cycle is fresh!")

    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 07.1 Complete.")

if __name__ == '__main__':
    run_anti_plagiarism()