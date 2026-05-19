import os
import sqlite3
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load API keys
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
BATCH_SIZE = 100  # How many headlines to send per API call
TOP_N_TO_SCAN = 15000 # How deep into the daily anomalies we want to look
PROMPT_PATH = os.path.join(BASE_DIR, "topic_filter.md")

def chunk_list(data_list, chunk_size):
    """Yield successive chunks from a list."""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]

def enrich_ai_data():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 08: DeepSeek AI Enrichment Layer...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create the new enrichment table
    cursor.execute('DROP TABLE IF EXISTS daily_ai_enrichment')
    cursor.execute('CREATE TABLE daily_ai_enrichment (date TEXT, gkg_record_id TEXT, is_ai_related INTEGER)')
    conn.commit()

    # 2. Grab the Top 5,000 unique headlines
    cursor.execute('''
        SELECT gkg_record_id, headline
        FROM daily_headline_scores 
        WHERE date = ? 
        GROUP BY gkg_record_id, headline
        ORDER BY MAX(anomaly_score) DESC 
        LIMIT ?
    ''', (today_str, TOP_N_TO_SCAN))
    
    articles = cursor.fetchall()
    if not articles:
        print("❌ No articles found for today. Did Step 07 run successfully?")
        conn.close()
        return

    print(f"Loaded {len(articles)} headlines. Slicing into batches of {BATCH_SIZE}...")
    batches = list(chunk_list(articles, BATCH_SIZE))
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    # 3. The Sorter Prompt
   # 3. Read the Sorter Prompt from the markdown file
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        system_prompt = f.read()

    total_ai_found = 0

    # 4. Loop through the batches and send to DeepSeek
    for i, batch in enumerate(batches):
        print(f"Processing Batch {i+1} of {len(batches)}...")
        
        payload = [{"id": g_id, "headline": h} for g_id, h in batch]
        user_prompt = f"Classify the following headlines:\n{json.dumps(payload)}"
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0 # Zero creativity, just strict classification
            )
            
            ai_output = json.loads(response.choices[0].message.content)
            results = ai_output.get("results", [])
            
            # Save the results of this batch to the database
            insert_data = []
            for item in results:
                is_ai_int = 1 if item.get("is_ai") else 0
                if is_ai_int == 1:
                    total_ai_found += 1
                insert_data.append((today_str, item.get("id"), is_ai_int))
                
            cursor.executemany('INSERT INTO daily_ai_enrichment VALUES (?, ?, ?)', insert_data)
            conn.commit()
            
            # Be polite to the API rate limits
            time.sleep(1) 
            
        except Exception as e:
            print(f"❌ Error on batch {i+1}: {e}")

    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Enrichment Complete! Found {total_ai_found} AI-related articles out of {len(articles)}.")

if __name__ == '__main__':
    enrich_ai_data()
