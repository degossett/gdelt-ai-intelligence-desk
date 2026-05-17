import os
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = r"C:\Users\schli\OneDrive\Documents\gdelt"
DB_PATH = os.path.join(BASE_DIR, r"gdelt_Data\gdelt_brain.db")
HTML_PATH = os.path.join(BASE_DIR, f"GDELT_AI_Briefing_{datetime.now().strftime('%Y-%m-%d')}.html")

def build_ai_ui():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 09: Building AI Executive Briefing HTML...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fetch AI clusters
    cursor.execute('''
        SELECT topic_rank, topic_name, summary, article_ids 
        FROM daily_ai_clusters 
        WHERE date = ? 
        ORDER BY topic_rank ASC
    ''', (today_str,))
    clusters = cursor.fetchall()

    if not clusters:
        print("❌ No AI clusters found for today. Make sure Step 08 (DeepSeek) ran successfully.")
        conn.close()
        return

    # 2. Fetch article metadata
    cursor.execute('''
        SELECT gkg_record_id, article_url, headline, anomaly_score
        FROM daily_headline_scores
        WHERE date = ?
    ''', (today_str,))
    
    article_lookup = {}
    for gkg_id, url, headline, score in cursor.fetchall():
        if gkg_id not in article_lookup:
            article_lookup[gkg_id] = {"url": url, "headline": headline, "score": score}

    # 3. Build the HTML Header
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>GDELT AI Executive Briefing - {today_str}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; line-height: 1.6; margin: 0; padding: 20px 50px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .header-info {{ font-size: 1.1em; color: #7f8c8d; margin-bottom: 30px; }}
            .cluster-card {{ background: #fff; border-radius: 8px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 6px solid #3498db; }}
            .cluster-title {{ font-size: 1.5em; color: #2980b9; margin-top: 0; margin-bottom: 10px; }}
            .cluster-summary {{ font-size: 1.1em; color: #34495e; background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-style: italic; }}
            .sources-title {{ font-weight: bold; margin-bottom: 10px; color: #7f8c8d; text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; }}
            .source-list {{ list-style-type: none; padding: 0; margin: 0; }}
            .source-item {{ margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}
            .source-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
            .source-link {{ color: #e74c3c; text-decoration: none; font-weight: 500; }}
            .source-link:hover {{ text-decoration: underline; }}
            .anomaly-score {{ font-family: monospace; color: #95a5a6; font-size: 0.9em; margin-left: 10px; }}
        </style>
    </head>
    <body>
        <h1>🌐 GDELT AI Executive Briefing</h1>
        <div class="header-info"><strong>Date:</strong> {today_str} | <strong>Top Events Identified:</strong> {len(clusters)}</div>
    """

    # 4. Inject Clusters into HTML
    for rank, name, summary, ids_str in clusters:
        html_content += f"""
        <div class="cluster-card">
            <h2 class="cluster-title">#{rank}: {name}</h2>
            <div class="cluster-summary">{summary}</div>
            <div class="sources-title">Top Underlying Sources:</div>
            <ul class="source-list">
        """
        
        # Get matching articles
        article_ids = [aid.strip() for aid in ids_str.split(',') if aid.strip()]
        topic_articles = [article_lookup[aid] for aid in article_ids if aid in article_lookup]
                
        # --- THE CAP: Sort by anomaly score and keep only top 3 ---
        topic_articles = sorted(topic_articles, key=lambda x: x['score'], reverse=True)[:3]
        
        # Add the articles to the HTML
        for data in topic_articles:
            score_display = f"{data['score']:.2f}"
            html_content += f"""
                <li class="source-item">
                    <a href="{data['url']}" target="_blank" class="source-link">{data['headline']}</a>
                    <span class="anomaly-score">(Anomaly Score: {score_display})</span>
                </li>
            """
        
        html_content += """
            </ul>
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    # 5. Save the file (Hard Overwrite)
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)

    conn.close()
    print(f"✅ Success! Report generated at: {HTML_PATH}")

if __name__ == '__main__':
    build_ai_ui()