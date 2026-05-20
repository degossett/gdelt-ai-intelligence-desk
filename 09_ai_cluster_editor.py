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
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 09: AI Editorial Review (With Memory)...")
    
    if not DEEPSEEK_API_KEY:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. FETCH THE AI'S MEMORY (YESTERDAY'S REPORT) ---
    # Find the most recent date in the DB that is NOT today
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
    
    print(f"🧠 Loaded Memory:\n{yesterday_context}")

    # --- 2. FETCH TODAY'S RAW CLUSTERS ---
    cursor.execute('''
        SELECT id, raw_cluster_name, cluster_keywords, cluster_size 
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
    for cluster_id, raw_name, keywords, size in today_clusters:
        cursor.execute('''
            SELECT headline 
            FROM daily_headline_scores 
            WHERE cluster_id = ? AND date = ?
            LIMIT 15
        ''', (cluster_id, today_str))
        headlines = [row[0] for row in cursor.fetchall()]
        
        cluster_data_for_prompt.append({
            "id": cluster_id,
            "raw_name": raw_name,
            "keywords": keywords,
            "size": size,
            "headlines": headlines
        })

    # Notice the new "YOUR MEMORY" injection in the prompt below
    system_prompt = f"""
    You are the Chief Editor for an intelligence desk. 
    You are reviewing today's clustered data to write an executive briefing.
    
    YOUR EDITORIAL GUIDELINES:
    {guidelines}
    
    YOUR MEMORY (CRITICAL):
    {yesterday_context}
    DO NOT report on the exact same events as the Previous Report unless there is a MASSIVE, brand-new development today. If a cluster is just lingering coverage of yesterday's news, down-rank its importance or write the summary to explicitly highlight only the NEW updates.

    Read the provided JSON list of today's clusters. 
    For each cluster, provide:
    1. "topic_name": A clean, executive title.
    2. "summary": A dense, analytical summary (3-4 sentences) following the guidelines.
    3. "topic_rank": Rank them from 1 to N (1 being the most important).

    You MUST return strictly valid JSON in this exact format:
    {{
        "edited_clusters": [
            {{"id": 1, "topic_name": "Title", "summary": "Summary text", "topic_rank": 1}}
        ]
    }}
    """

    print("🚀 Sending today's data to DeepSeek for analysis...")
    
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
        
        # --- 5. UPDATE THE DATABASE ---
        for item in parsed_data.get("edited_clusters", []):
            cursor.execute('''
                UPDATE daily_ai_clusters
                SET topic_name = ?, summary = ?, topic_rank = ?
                WHERE id = ? AND date = ?
            ''', (item['topic_name'], item['summary'], item['topic_rank'], item['id'], today_str))
        
        conn.commit()
        print("✅ Successfully updated clusters with AI editorial review!")
        
    except Exception as e:
        print(f"❌ ERROR connecting to DeepSeek or parsing JSON: {e}")
        if 'response' in locals():
            print(response.text)
            
    conn.close()

if __name__ == '__main__':
    edit_clusters()
