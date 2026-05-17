import os
import glob
import sqlite3
import pandas as pd
import re
import langid
import html
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

# Restrict langid to common global languages so it doesn't hallucinate on short headlines
langid.set_languages(['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ar'])

def get_latest_gdelt_file():
    """Finds the most recently downloaded GLOBAL gdelt CSV."""
    search_pattern = os.path.join(DATA_DIR, "gdelt_gkg_GLOBAL_*.csv")
    files = glob.glob(search_pattern)
    if not files:
        raise FileNotFoundError("No GLOBAL CSVs found. Run 01 script first.")
    return max(files, key=os.path.getctime)

def is_english(headline):
    """Unescapes HTML entities, then uses Regex + langid to block foreign text."""
    if not headline or len(headline.strip()) < 10: 
        return False
        
    # THE FIX: Pull the mask off the HTML-encoded text first!
    decoded_headline = html.unescape(headline)
    
    # 1. The Fast Filter: Drop heavy non-Latin alphabets (Russian, Greek, Chinese)
    foreign_chars = re.sub(r'[a-zA-Z0-9\s.,!?\'"|\-()\[\]{}&#%]', '', decoded_headline)
    if len(decoded_headline) > 0 and (len(foreign_chars) / len(decoded_headline)) > 0.05:
        return False
        
    # 2. The Smart Filter: Drop Latin-based foreign languages (Spanish, French)
    try:
        lang, _ = langid.classify(decoded_headline)
        return lang == 'en'
    except:
        return False

def extract_headline(extras_string):
    """Uses regex to pull the text between <PAGE_TITLE> and </PAGE_TITLE>"""
    if pd.isna(extras_string):
        return ""
    match = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', str(extras_string), re.IGNORECASE)
    if match:
        headline = match.group(1).strip()
        # Only return the headline if it passes our rigorous English filter
        if is_english(headline):
            # Return the clean, unescaped text so your final report looks readable!
            return html.unescape(headline)
    return ""

def process_corpus():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 03: Extracting TRUE English Corpus...")
    
    latest_file = get_latest_gdelt_file()
    print(f"Reading data from: {os.path.basename(latest_file)}")
    
    use_cols = ['GKGRECORDID', 'DocumentIdentifier', 'V2Themes', 'V2Persons', 'V2Organizations', 'V2Locations', 'Extras']
    df = pd.read_csv(latest_file, usecols=use_cols, low_memory=False)
    
    df = df.dropna(subset=['GKGRECORDID', 'Extras'])
    
    print("Parsing XML and running true language detection (this takes a few minutes)...")
    df['headline'] = df['Extras'].apply(extract_headline)
    
    corpus_df = df[df['headline'] != ""]
    
    corpus_df['DocumentIdentifier'] = corpus_df['DocumentIdentifier'].fillna("")
    corpus_df['V2Persons'] = corpus_df['V2Persons'].fillna("")
    corpus_df['V2Organizations'] = corpus_df['V2Organizations'].fillna("")
    corpus_df['V2Themes'] = corpus_df['V2Themes'].fillna("")
    corpus_df['V2Locations'] = corpus_df['V2Locations'].fillna("")
    
    final_df = corpus_df[['GKGRECORDID', 'DocumentIdentifier', 'V2Themes', 'V2Persons', 'V2Organizations', 'V2Locations', 'headline']].copy()
    final_df.columns = ['gkg_record_id', 'article_url', 'cluster_tags', 'persons', 'organizations', 'locations', 'headline']
    final_df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    print("Dropping duplicate GDELT IDs...")
    final_df = final_df.drop_duplicates(subset=['gkg_record_id'])
    
    print(f"Successfully extracted {len(final_df)} TRUE English records.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Writing to SQLite database...")
    final_df.to_sql('article_corpus', conn, if_exists='replace', index=False)
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_gkg_id ON article_corpus(gkg_record_id)')
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 03 Complete.")

if __name__ == '__main__':
    process_corpus()
