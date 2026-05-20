import os
import sqlite3
import json
from datetime import datetime
import requests

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
GUIDELINES_PATH = os.path.join(BASE_DIR, "editorial_guidelines.md")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def edit_clusters():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 09: AI Editorial Review (Using RowID Shield)...")
    
    if not DEEPSEEK_API_KEY:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. FETCH THE AI'S MEMORY (YESTERDAY'S REPORT) ---
    cursor.execute('''
        SELECT DISTINCT date FROM daily_ai_clusters 
        WHERE date < ? 
        ORDER BY date DESC LIMIT 1
    ''', (today_str,))
    last_date_row = cursor.fetchone()
    
    yesterday_context = "No previous reports found. This is the first run."
    if last_date_row:
        last_date = last_date_row[0]
        cursor.execute('''
            SELECT topic_name, summary 
            FROM daily_ai_clusters 
            WHERE date = ?
        ''', (last_date,))
        old_clusters = cursor.fetchall()
        
        if old_clusters:
            yesterday_context = f"PREVIOUS REPORT TOPICS ({last_date}):\n"
            for name, summary in old_clusters:
                yesterday_context += f"- {name}: {summary}\n"

    # --- 2. FETCH TODAY'S RAW CLUSTERS (Using implicit rowid) ---
    print("Fetching today's raw clusters using database rowid...")
    cursor.execute('''
        SELECT rowid, raw_cluster_name, cluster_keywords, cluster_size 
        FROM daily_ai_clusters 
        WHERE date = ?
    ''', (today_str,))
    today_clusters = cursor.fetchall()

    if not today_clusters:
        print("❌ No raw clusters found for today. Make sure Step 08 ran successfully.")
        conn.close()
        return

    # --- 3. READ EDITORIAL GUIDELINES ---
    guidelines = "Provide a professional summary of the events."
    if os.path.exists(GUIDELINES_PATH):
        with open(GUIDELINES_PATH, 'r', encoding='utf-8') as f:
            guidelines = f.read()

    # --- 4. PREPARE THE DATA FOR DEEPSEEK ---
    cluster_data_for_prompt = []
    for cluster_rowid, raw_name, keywords, size in today_clusters:
        # We look up headlines matching this specific row's cluster properties
        cursor.execute('''
            SELECT headline 
            FROM daily_headline_scores 
            WHERE date = ? 
            AND cluster_id = (SELECT rowid FROM daily_ai_clusters WHERE rowid = ? AND date = ?)
            LIMIT 15
        ''', (today_str, cluster_rowid, today_str))
        headlines = [row[0] for row in cursor.fetchall()]
        
        cluster_data_for_prompt.append({
            "id": cluster_rowid,  # DeepSeek sees this as a clean integer ID
            "raw_name": raw_name,
            "keywords": keywords,
            "size": size,
            "headlines": headlines
        })

    system_prompt = f"""
    You are the Chief Editor for an intelligence desk. 
    You are reviewing today's clustered data to write an executive briefing.
    
    YOUR EDITORIAL GUIDELINES:
    {guidelines}
    
    YOUR MEMORY (CRITICAL):
    {yesterday_context}
    DO NOT report on the exact same events as the Previous Report unless there is a MASSIVE, brand-new development today.

    TASK:
    Read the provided JSON list of today's clusters. For each item, you must preserve its tracking ID.
    Provide:
    1. "id": The EXACT, unmodified integer ID provided in the input data. Do not re-number this!
    2. "topic_name": A clean, executive title.
    3. "summary": A dense, analytical summary (3-4 sentences).
    4. "topic_rank": Rank them from 1 to N (1 being most important).

    You MUST return strictly valid JSON in this exact format:
    {{
        "edited_clusters": [
            {{"id": 999, "topic_name": "Title", "summary": "Summary text", "topic_rank": 1}}
        ]
    }}
    """

    print("🚀 Sending data to DeepSeek...")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(cluster_data_for_prompt)}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result_json = response.json()
        
        content = result_json['choices'][0]['message']['content']
        parsed_data = json.loads(content)
        
        print("📥 AI Response received. Syncing back to database...")
        
        # --- 5. UPDATE THE DATABASE USING THE MATCHED ROWID ---
        rows_updated = 0
        for item in parsed_data.get("edited_clusters", []):
            cursor.execute('''
                UPDATE daily_ai_clusters
                SET topic_name = ?, summary = ?, topic_rank = ?
                WHERE rowid = ? AND date = ?
            ''', (item['topic_name'], item['summary'], item['topic_rank'], item['id'], today_str))
            rows_updated += cursor.rowcount
        
        conn.commit()
        print(f"✅ Successfully matched and updated {rows_updated} database rows via RowID!")
        
    except Exception as e:
        print(f"❌ ERROR connecting to DeepSeek or parsing JSON: {e}")
        if 'response' in locals():
            print(response.text)
            
    conn.close()

if __name__ == '__main__':
    edit_clusters()
