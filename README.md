# 🌐 GDELT Automated Intelligence Desk

An automated, cloud-native intelligence pipeline that pulls daily global event data from GDELT—**scanning over 150,000+ English news headlines from around the world every day**—processes it using natural language processing (NLP), and generates an AI-curated morning briefing. 

Out of the box, this desk is configured to track **Artificial Intelligence and its geopolitical impact**. However, the architecture is completely topic-agnostic and can be pivoted to track *any* global industry or event in minutes without altering a single line of code.

## ⚙️ Architecture
This project runs entirely in the cloud with zero manual intervention:
* **Compute:** GitHub Actions & Docker (Ubuntu Linux)
* **Storage:** Google Cloud Storage (GCP Bucket)
* **Database:** SQLite (`gdelt_brain.db`)
* **AI Provider:** DeepSeek API
* **Delivery:** Automated HTML injected directly into an SMTP Email

## 🎯 How to Track a Different Topic
Want to track Biotech, Space Exploration, Crypto Markets, or Global Supply Chains instead of AI? You do not need to touch the Python scripts. Simply edit the two configuration markdown files:

1. **`topic_filter.md`:** * Change the `TOPIC: [Name]` on line 1 (this dynamically updates your email subject line and HTML header).
   * Rewrite the "True" and "False" classification criteria to tell the AI exactly what constitutes a relevant headline for your new field.
2. **`editorial_guidelines.md`:** * Update the guidelines to tell the AI what makes a story "highly interesting" or "important" in your new industry (e.g., FDA approvals for Biotech, or rocket launches for Space). 
   * Dictate the tone and depth of the final briefing summaries.
  
## 🔐 Setting Up Your Secret Vault
To run this pipeline in your own repository, you must store your API keys and passwords securely. **Never hardcode these into your scripts.**

1. In your GitHub repository, click on the **Settings** tab.
2. On the left sidebar, scroll down to **Secrets and variables** and click **Actions**.
3. Click the green **New repository secret** button and add the following exactly as spelled:

* `DEEPSEEK_API_KEY`: Your DeepSeek API key for AI generation.
* `EMAIL_APP_PASSWORD`: The 16-character Google App Password for the sender email (no spaces).
* `GCP_CREDENTIALS`: The entire contents of your Service Account JSON file for Google Cloud Storage access.
* `MY_SECRET_EMAIL`: The executive inbox receiving the report (e.g., *you@company.com*).
* `SENDER_EMAIL`: The Gmail address sending the report (e.g., *yourbot@gmail.com*).

## 🚀 The Daily Pipeline
Every day, the GitHub Actions orchestrator triggers `.github/workflows/daily_pipeline.yml`, which executes the following steps:

1. **Cloud Authentication:** Logs into Google Cloud and downloads the historical SQLite memory bank.
2. **Containerization:** Builds an isolated Docker environment and installs all Python dependencies.
3. **Data Acquisition:** Downloads the latest 24 hours of global event data from the GDELT project.
4. **Targeted Extraction & Scoring:** Calculates TF-IDF baselines and uses DeepSeek to aggressively filter the 150,000+ daily headlines, isolating only the events related to your target topic (defined in `topic_filter.md`). 
5. **Clustering & Sequencing:** Groups the isolated events into distinct narrative clusters and sequences them by their global anomaly score and geopolitical importance.
6. **AI Enrichment:** Passes the sequenced clusters back to DeepSeek for deep analysis and summarization according to `editorial_guidelines.md`.
7. **Report Generation:** Compiles the AI analysis into a beautifully formatted, dynamic HTML briefing.
8. **Delivery:** Injects the HTML directly into the body of an email and sends it to the executive inbox.
9. **Database Optimization:** Executes a daily cleanup script (`12_database_cleanup.py`) that purges records older than 30 days and compresses the SQLite database (`VACUUM`) to prevent cloud bloat.
10. **Memory Sync:** Uploads the updated, compressed SQLite database back to Google Cloud Storage so the AI remembers today's baseline for tomorrow.

## ⏰ Changing the Schedule
By default, GitHub Actions operate on **UTC time**. To change when your intelligence desk wakes up, open your workflow file (e.g., `.github/workflows/daily_pipeline.yml`) and modify the `cron` schedule string at the top of the file.

```yaml
on:
  schedule:
    - cron: '0 7 * * *' # Runs at 7:00 AM UTC
