import os
import glob
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
CSV_EXPORT_PATH = os.path.join(DATA_DIR, "master_cluster_matrix_30d.csv")

def get_latest_gdelt_file():
    search_pattern = os.path.join(DATA_DIR, "gdelt_gkg_GLOBAL_*.csv")
    files = glob.glob(search_pattern)
    if not files: raise FileNotFoundError("No GLOBAL GDELT CSVs found.")
    return max(files, key=os.path.getctime)

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_cluster_counts (
            date TEXT,
            cluster_name TEXT,
            article_count INTEGER,
            PRIMARY KEY (date, cluster_name)
        )
    ''')
    conn.commit()
    return conn

def process_entities(series, prefix=""):
    exploded = series.dropna().str.split(';').explode().str.split(',').str[0]
    exploded = exploded[exploded != '']
    if prefix: exploded = prefix + exploded
    return exploded

def process_locations(series, prefix="COUNTRY_"):
    exploded = series.dropna().str.split(';').explode()
    exploded = exploded[exploded != '']
    full_names = exploded.str.split('#').str[1].dropna()
    countries = full_names.str.split(',').str[-1].str.strip()
    countries = countries[countries != '']
    return prefix + countries

def process_today_counts():
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 02: Unified Cluster Counts...")
    
    latest_file = get_latest_gdelt_file()
    use_cols = ['V2Themes', 'V2Persons', 'V2Organizations', 'V2Locations']
    df = pd.read_csv(latest_file, usecols=use_cols, low_memory=False)
    
    themes_series = process_entities(df['V2Themes'], prefix="")
    # NEW: Drop the World Languages hallucination tags!
    themes_series = themes_series[~themes_series.str.startswith('TAX_WORLDLANGUAGES_')]
    
    persons_series = process_entities(df['V2Persons'], prefix="PERSON_")
    orgs_series = process_entities(df['V2Organizations'], prefix="ORG_")
    locs_series = process_locations(df['V2Locations'], prefix="COUNTRY_")
    
    all_clusters = pd.concat([themes_series, persons_series, orgs_series, locs_series], ignore_index=True)
    today_counts = all_clusters.value_counts().reset_index()
    today_counts.columns = ['cluster_name', 'article_count']
    today_counts['date'] = today_str
    
    conn = initialize_database()
    conn.execute('DELETE FROM daily_cluster_counts WHERE date = ?', (today_str,))
    conn.commit()
    
    today_counts.to_sql('daily_cluster_counts', conn, if_exists='append', index=False, chunksize=5000)

    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    conn.execute('DELETE FROM daily_cluster_counts WHERE date < ?', (thirty_days_ago,))
    conn.commit()

    history_df = pd.read_sql_query("SELECT * FROM daily_cluster_counts", conn)
    if not history_df.empty:
        matrix_df = history_df.pivot(index='cluster_name', columns='date', values='article_count').fillna(0)
        if today_str in matrix_df.columns:
            matrix_df = matrix_df.sort_values(by=today_str, ascending=False)
        matrix_df.to_csv(CSV_EXPORT_PATH)
    
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 02 Complete.")

if __name__ == '__main__':
    process_today_counts()
