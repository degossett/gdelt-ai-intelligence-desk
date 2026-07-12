import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")
HTML_PATH = os.path.join(BASE_DIR, f"GDELT_Briefing_{datetime.now().strftime('%Y-%m-%d')}.html")
PROMPT_PATH = os.path.join(BASE_DIR, "topic_filter.md")

def build_ai_ui():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 10: Building Mobile-Friendly Briefing...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- DYNAMIC TOPIC EXTRACTION ---
    topic_name = "Global Events" # Default fallback
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith("TOPIC:"):
                topic_name = first_line.replace("TOPIC:", "").strip()

    # 1. Fetch AI clusters
    cursor.execute('''
        SELECT topic_rank, topic_name, summary, article_ids 
        FROM daily_ai_clusters 
        WHERE date = ? 
        ORDER BY topic_rank ASC
    ''', (today_str,))
    clusters = cursor.fetchall()

    if not clusters:
        print("❌ No clusters found for today.")
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

    # 3. Build the Mobile-Optimized HTML Header
    # We added the viewport meta tag and stripped out the heavy CSS padding/shadows.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GDELT Briefing: {topic_name}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff; color: #1a1a1a; line-height: 1.5; margin: 0; padding: 15px; font-size: 16px; }}
            h1 {{ color: #0056b3; font-size: 22px; border-bottom: 1px solid #ddd; padding-bottom: 8px; margin-bottom: 5px; line-height: 1.2; }}
            .header-info {{ font-size: 14px; color: #555; margin-bottom: 25px; }}
            .cluster-card {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
            .cluster-title {{ font-size: 18px; color: #000; margin-top: 0; margin-bottom: 8px; }}
            .cluster-summary {{ font-size: 15px; color: #333; margin-bottom: 15px; }}
            .sources-title {{ font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; margin-bottom: 8px; }}
            .source-list {{ list-style-type: none; padding: 0; margin: 0; }}
            .source-item {{ margin-bottom: 10px; font-size: 14px; }}
            .source-link {{ color: #0056b3; text-decoration: none; font-weight: 500; display: block; margin-bottom: 2px; }}
            .source-link:hover {{ text-decoration: underline; }}
            .anomaly-score {{ color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h1>{topic_name}</h1>
        <div class="header-info">Date: {today_str} | Events: {len(clusters)}</div>
    """

    # 4. Inject Clusters into HTML
    for rank, name, summary, ids_str in clusters:
        html_content += f"""
        <div class="cluster-card">
            <h2 class="cluster-title">Topic: {name}</h2>
            <div class="cluster-summary">{summary}</div>
            <div class="sources-title">Key Sources</div>
            <ul class="source-list">
        """
        
        # Get matching articles
        article_ids = [aid.strip() for aid in ids_str.split(',') if aid.strip()]
        topic_articles = [article_lookup[aid] for aid in article_ids if aid in article_lookup]
                
        # Keep only top 3 by anomaly score
        topic_articles = sorted(topic_articles, key=lambda x: x['score'], reverse=True)[:3]
        
        # Add the articles to the HTML
        for data in topic_articles:
            try:
                domain = urlparse(data['url']).netloc.replace('www.', '')
            except:
                domain = "Source"
                
            html_content += f"""
                <li class="source-item">
                    <a href="{data['url']}" target="_blank" class="source-link">{data['headline']}</a>
                    <span class="anomaly-score">{domain} (Score: {data['score']:.2f})</span>
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

    # 5. Save the file
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)

    conn.close()
    print(f"✅ Success! Mobile report generated at: {HTML_PATH}")

if __name__ == '__main__':
    build_ai_ui()
