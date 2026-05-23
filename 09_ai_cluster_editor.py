import os
import sqlite3
import json
import traceback
import sys
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
GUIDELINES_PATH = os.path.join(BASE_DIR, "editorial_guidelines.md")

def generate_ai_briefs():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 09: DeepSeek AI Clustering & Editorial Review...")
    
    if not DEEPSEEK_API_KEY:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set.")
        sys.exit(1)

    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. READ EDITORIAL GUIDELINES ---
    try:
        with open(GUIDELINES_PATH, 'r', encoding='utf-8') as f:
            editorial_wiki = f.read()
    except FileNotFoundError:
        print(f"❌ Error: {GUIDELINES_PATH} not found!")
        sys.exit(1)

    # --- 2. FETCH THE AI'S MEMORY (YESTERDAY'S REPORT TITLES ONLY) ---
    print("🧠 Checking database for previous report memory...")
    # Safe check to see if the table even exists yet
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_ai_clusters'")
    table_exists = cursor.fetchone()
    
    yesterday_context = "No previous reports found. This is the first run."
    if table_exists:
        cursor.execute('''
            SELECT DISTINCT date FROM daily_ai_clusters 
            WHERE date < ? 
            ORDER BY date DESC LIMIT 1
        ''', (today_str,))
        last_date_row = cursor.fetchone()
        
        if last_date_row:
            last_date = last_date_row[0]
            # ONLY fetch the topic names, skipping the summaries completely!
            cursor.execute('''
                SELECT topic_name 
                FROM daily_ai_clusters 
                WHERE date = ?
            ''', (last_date,))
            old_clusters = cursor.fetchall()
            
            if old_clusters:
                yesterday_context = f"YESTERDAY'S TOPICS ({last_date}):\n"
                for row in old_clusters:
                    yesterday_context += f"- {row[0]}\n"
    
    print(f"Loaded Memory Context:\n{yesterday_context}")

    # --- 3. GRAB THE ENRICHED HEADLINES (FROM SCRIPT 08) ---
    print("📥 Fetching today's AI-enriched headlines...")
    try:
        cursor.execute('''
            SELECT d.gkg_record_id, d.headline, MAX(d.anomaly_score) as max_score
            FROM daily_headline_scores d
            JOIN daily_ai_enrichment e ON d.gkg_record_id = e.gkg_record_id
            WHERE d.date = ? AND e.is_ai_related = 1
            GROUP BY d.gkg_record_id, d.headline
            ORDER BY max_score DESC 
        ''', (today_str,))
        articles = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ ERROR reading enriched data. Did Script 08 run? Details: {e}")
        conn.close()
        sys.exit(1)

    if not articles:
        print("⚠️ No AI-related articles found for today. Skipping clustering.")
        conn.close()
        return

    print(f"Loaded {len(articles)} relevant headlines. Formatting for DeepSeek...")
    payload = [{"id": g_id, "score": round(s, 2), "headline": h} for g_id, h, s in articles]
    payload_json = json.dumps(payload)

    # --- 4. BUILD THE PROMPTS ---
    system_prompt = f"""
    You are the Editor-in-Chief of a global intelligence desk. 
    You must strictly adhere to the principles outlined in the following internal editorial wiki:
    
    --- START EDITORIAL WIKI ---
    {editorial_wiki}
    --- END EDITORIAL WIKI ---
    
    --- START HARD BLACKLIST (YESTERDAY'S NEWS) ---
    {yesterday_context}
    CRITICAL RULE: You are strictly forbidden from writing about the topics listed above. Do not include them in your output unless there is a MASSIVE, fundamentally new geopolitical development today. If it is just lingering syndication of yesterday's news, IGNORE IT completely.
    --- END HARD BLACKLIST ---
    
    You MUST return your answer in strictly valid JSON format exactly matching this schema:
    {{
        "topics": [
            {{
                "topic_name": "Clear name of the event",
                "summary": "5-to-7 sentence comprehensive analytical summary.",
                "article_ids": ["id1", "id2"]
            }}
        ]
    }}
    """
    
    user_prompt = f"Here is today's raw anomaly data. Synthesize this into the top 15 to 20 events based strictly on our editorial guidelines:\n{payload_json}"

    print("🚀 Sending payload to DeepSeek (This may take 30-60 seconds)...")
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1 
        )
        
        # --- 5. PARSE AND ENFORCE ---
        ai_output = json.loads(response.choices[0].message.content)
        raw_topics = ai_output.get("topics", [])
        
        # THE HARD ENFORCER: Python checks the math, not the AI
        topics = [t for t in raw_topics if len(t.get("article_ids", [])) >= 2]
        
        print(f"✅ DeepSeek generated {len(raw_topics)} intelligence clusters.")
        if len(raw_topics) != len(topics):
            print(f"✂️ Python Enforcer deleted {len(raw_topics) - len(topics)} single-source clusters that broke the rules!")

        # --- 6. SAVE TO DATABASE ---
        cursor.execute('DROP TABLE IF EXISTS daily_ai_clusters')
        cursor.execute('''
            CREATE TABLE daily_ai_clusters (
                date TEXT, 
                topic_rank INTEGER, 
                topic_name TEXT, 
                summary TEXT, 
                article_ids TEXT
            )
        ''')
        
        insert_data = []
        for index, topic in enumerate(topics):
            insert_data.append((
                today_str, 
                index + 1, 
                topic.get("topic_name", "Unknown Topic"), 
                topic.get("summary", ""), 
                ",".join(topic.get("article_ids", []))
            ))
            
        cursor.executemany('INSERT INTO daily_ai_clusters VALUES (?, ?, ?, ?, ?)', insert_data)
        conn.commit()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 09 Complete. Saved {len(insert_data)} clusters.")

    except Exception as e:
        print(f"❌ DeepSeek or Parsing Error:\n{traceback.format_exc()}")
        sys.exit(1)

    conn.close()

if __name__ == '__main__':
    generate_ai_briefs()
