import os
import sqlite3
import json
from datetime import datetime
import urllib.request
import urllib.error
import traceback
import sys

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 09: Bulletproof AI Editorial Review...", flush=True)
    
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set.", flush=True)
        sys.exit(1)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
    DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
    GUIDELINES_PATH = os.path.join(BASE_DIR, "editorial_guidelines.md")

    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 🔍 1. LIVE SCHEMA DETECTION
    cursor.execute("PRAGMA table_info(daily_ai_clusters)")
    ai_cols = [r[1] for r in cursor.fetchall()]
    print(f"📊 Live Schema Detection (daily_ai_clusters): {ai_cols}", flush=True)

    if not ai_cols:
        print("❌ ERROR: daily_ai_clusters table does not exist or is empty.", flush=True)
        conn.close()
        sys.exit(1)

    # Dynamically match column names to prevent syntax errors
    name_col = 'raw_cluster_name' if 'raw_cluster_name' in ai_cols else ('cluster_name' if 'cluster_name' in ai_cols else ai_cols[0])
    
    select_cols = ['rowid', name_col]
    if 'cluster_keywords' in ai_cols: select_cols.append('cluster_keywords')
    elif 'keywords' in ai_cols: select_cols.append('keywords')
    if 'cluster_size' in ai_cols: select_cols.append('cluster_size')
    elif 'size' in ai_cols: select_cols.append('size')

    cols_str = ", ".join(select_cols)
    print(f"Executing: SELECT {cols_str} FROM daily_ai_clusters WHERE date = '{today_str}'", flush=True)
    
    cursor.execute(f"SELECT {cols_str} FROM daily_ai_clusters WHERE date = ?", (today_str,))
    today_clusters = cursor.fetchall()

    if not today_clusters:
        print("⚠️ No raw clusters found for today. Skipping AI text generation.", flush=True)
        conn.close()
        return

    # 🧠 2. FETCH HISTORICAL CONTEXT
    yesterday_context = "No previous reports found."
    try:
        cursor.execute("SELECT DISTINCT date FROM daily_ai_clusters WHERE date < ? ORDER BY date DESC LIMIT 1", (today_str,))
        last_date_row = cursor.fetchone()
        if last_date_row:
            last_date = last_date_row[0]
            cursor.execute(f"SELECT {name_col} FROM daily_ai_clusters WHERE date = ? LIMIT 10", (last_date,))
            yesterday_context = f"Previous topics from {last_date}: " + ", ".join([r[0] for r in cursor.fetchall() if r[0]])
    except Exception as e:
        print(f"⚠️ History fetch bypass: {e}", flush=True)

    # 📋 3. READ EDITORIAL GUIDELINES
    guidelines = "Provide a dense executive summary of today's key events."
    if os.path.exists(GUIDELINES_PATH):
        with open(GUIDELINES_PATH, 'r', encoding='utf-8') as f:
            guidelines = f.read()

    # 🏗️ 4. BUILD PROMPT PAYLOAD
    cluster_data_for_prompt = []
    cursor.execute("PRAGMA table_info(daily_headline_scores)")
    hl_cols = [r[1] for r in cursor.fetchall()]

    for row in today_clusters:
        rowid = row[0]
        c_name = row[1]
        
        headlines = []
        try:
            if 'cluster_id' in hl_cols:
                cursor.execute("SELECT headline FROM daily_headline_scores WHERE cluster_id = ? AND date = ? LIMIT 15", (rowid, today_str))
            elif 'cluster_name' in hl_cols:
                cursor.execute("SELECT headline FROM daily_headline_scores WHERE cluster_name = ? AND date = ? LIMIT 15", (c_name, today_str))
            else:
                cursor.execute("SELECT headline FROM daily_headline_scores WHERE date = ? LIMIT 15", (today_str,))
            headlines = [r[0] for r in cursor.fetchall()]
        except Exception as e:
            pass

        cluster_data_for_prompt.append({
            "id": rowid,
            "name": c_name,
            "headlines": headlines
        })

    system_prompt = f"""
    You are the Chief Editor for an intelligence desk.
    EDITORIAL GUIDELINES:
    {guidelines}
    
    MEMORY (DO NOT DUPLICATE THESE RECENT TOPICS):
    {yesterday_context}

    TASK:
    Review today's data. You must preserve the input integer tracking IDs precisely.
    Provide strictly valid JSON matching this schema:
    {{
        "edited_clusters": [
            {{"id": 123, "topic_name": "Executive Title", "summary": "Dense analytical summary", "topic_rank": 1}}
        ]
    }}
    """

    # 🚀 5. DEPENDENCY-FREE API CALL VIA URLLIB
    print("🚀 Dispatched payload to DeepSeek endpoints...", flush=True)
    url = "https://api.deepseek.com/v1/chat/completions"
    req_data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(cluster_data_for_prompt)}
        ],
        "response_format": {"type": "json_object"}
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(req_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            result_json = json.loads(res_body)
            content = result_json['choices'][0]['message']['content']
            parsed_data = json.loads(content)
            
            print("📥 Payload processed successfully. Syncing to database...", flush=True)
            
            # 💾 6. DYNAMIC DATABASE UPDATE
            rows_updated = 0
            for item in parsed_data.get("edited_clusters", []):
                t_name = item.get('topic_name', 'Global Event Update')
                summary = item.get('summary', '')
                rank = item.get('topic_rank', 1)
                target_id = item.get('id')
                
                set_clauses = []
                params = []
                if 'topic_name' in ai_cols:
                    set_clauses.append("topic_name = ?")
                    params.append(t_name)
                if 'summary' in ai_cols:
                    set_clauses.append("summary = ?")
                    params.append(summary)
                if 'topic_rank' in ai_cols:
                    set_clauses.append("topic_rank = ?")
                    params.append(rank)
                    
                if set_clauses:
                    sql = f"UPDATE daily_ai_clusters SET {', '.join(set_clauses)} WHERE rowid = ? AND date = ?"
                    params.extend([target_id, today_str])
                    cursor.execute(sql, params)
                    rows_updated += cursor.rowcount
            
            conn.commit()
            print(f"✅ Step 09 Complete! Successfully updated {rows_updated} database entries.", flush=True)

    except urllib.error.HTTPError as he:
        print(f"❌ HTTP Error from DeepSeek: {he.code} - {he.read().decode('utf-8')}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Extraction or mapping error: {e}", flush=True)
        sys.exit(1)

    conn.close()

if __name__ == '__main__':
    try:
        main()
    except Exception as global_err:
        print("\n💥 CRITICAL RECOVERY ERROR:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
