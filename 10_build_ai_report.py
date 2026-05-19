# 4. Inject Clusters into HTML
    for rank, name, summary, ids_str in clusters:
        html_content += f"""
        <div class="cluster-card">
            <h2 class="cluster-title">Topic: {name}</h2>
            <div class="cluster-summary"><strong>Quick Hit:</strong> {summary}</div>
            <div class="sources-title">Relevant Articles:</div>
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
            
            # Basic domain extraction for the source name
            try:
                from urllib.parse import urlparse
                domain = urlparse(data['url']).netloc.replace('www.', '')
            except:
                domain = "Source"
                
            html_content += f"""
                <li class="source-item">
                    <a href="{data['url']}" target="_blank" class="source-link">{data['headline']}</a>
                    <span class="anomaly-score">(Source: {domain} | Score: {score_display})</span>
                </li>
            """
        
        html_content += """
            </ul>
        </div>
        """
