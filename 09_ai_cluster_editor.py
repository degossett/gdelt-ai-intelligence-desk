import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load API keys from your .env file
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, r"gdelt_Data\gdelt_brain.db")
WIKI_PATH = os.path.join(BASE_DIR, "editorial_guidelines.md")

def generate_ai_briefs():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 08: DeepSeek AI Clustering (Global Top 2000 Unique)...")
    
    # 1. Read the Editorial Wiki
    try:
        with open(WIKI_PATH, 'r', encoding='utf-8') as f:
            editorial_wiki = f.read()
    except FileNotFoundError:
        print(f"❌ Error: {WIKI_PATH} not found! Please create your editorial_guidelines.md file.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Grab ONLY the headlines the Enrichment Layer flagged as AI-related
    cursor.execute('''
        SELECT d.gkg_record_id, d.headline, MAX(d.anomaly_score) as max_score
        FROM daily_headline_scores d
        JOIN daily_ai_enrichment e ON d.gkg_record_id = e.gkg_record_id
        WHERE d.date = ? AND e.is_ai_related = 1
        GROUP BY d.gkg_record_id, d.headline
        ORDER BY max_score DESC 
    ''', (today_str,))
    
    articles = cursor.fetchall()
    if not articles:
        print("❌ No articles found for today. Did Step 07 run successfully?")
        conn.close()
        return

    print(f"Loaded top {len(articles)} globally unique anomalous headlines. Formatting for DeepSeek...")

    payload = [{"id": g_id, "score": round(s, 2), "headline": h} for g_id, h, s in articles]
    payload_json = json.dumps(payload)

    # 3. The Prompts (Clean and Simple)
    system_prompt = f"""
    You are the Editor-in-Chief of a global intelligence desk. 
    You must strictly adhere to the principles outlined in the following internal editorial wiki:
    
    --- START EDITORIAL WIKI ---
    {editorial_wiki}
    --- END EDITORIAL WIKI ---
    
    You MUST return your answer in strictly valid JSON format exactly matching this schema:
    {{
        "topics": [
            {{
                "topic_name": "Clear name of the event",
                "summary": "3-to-4 sentence summary.",
                "article_ids": ["id1", "id2"]
            }}
        ]
    }}
    """
    
    user_prompt = f"Here is today's raw anomaly data. Synthesize this into the top 15 to 20 events based strictly on our editorial guidelines:\n{payload_json}"

    print("Sending payload to DeepSeek (This may take 30-45 seconds)...")
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
        
        # 4. Parse response
        ai_output = json.loads(response.choices[0].message.content)
        raw_topics = ai_output.get("topics", [])
        
        # --- THE HARD ENFORCER: Python checks the math, not the AI ---
        topics = [t for t in raw_topics if len(t.get("article_ids", [])) >= 2]
        
        print(f"✅ DeepSeek generated {len(raw_topics)} intelligence clusters.")
        if len(raw_topics) != len(topics):
            print(f"✂️ Python Enforcer deleted {len(raw_topics) - len(topics)} single-source clusters that broke the rules!")

        # 5. Save to database
        cursor.execute('DROP TABLE IF EXISTS daily_ai_clusters')
        cursor.execute('CREATE TABLE daily_ai_clusters (date TEXT, topic_rank INTEGER, topic_name TEXT, summary TEXT, article_ids TEXT)')
        
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
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Success! Step 08 Complete.")

    except Exception as e:
        print(f"❌ DeepSeek Error: {e}")

    conn.close()

if __name__ == '__main__':
    generate_ai_briefs()
