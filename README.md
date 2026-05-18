# 🌐 GDELT AI Intelligence Desk

An automated, cloud-native intelligence pipeline that pulls daily global event data from GDELT, processes it using natural language processing (NLP), and generates an AI-curated morning briefing **specifically focused on Artificial Intelligence and its geopolitical impact.**

## ⚙️ Architecture
This project runs entirely in the cloud with zero manual intervention:
* **Compute:** GitHub Actions & Docker (Ubuntu Linux)
* **Storage:** Google Cloud Storage (GCP Bucket)
* **Database:** SQLite (`gdelt_brain.db`)
* **AI Provider:** DeepSeek API
* **Delivery:** Automated SMTP Email

## 🚀 The Daily Pipeline
Every morning at 1:00 AM Mountain Time, the GitHub Actions orchestrator triggers `.github/workflows/daily_pipeline.yml`, which executes the following steps:

1. **Cloud Authentication:** Logs into Google Cloud and downloads the historical SQLite brain.
2. **Containerization:** Builds an isolated Docker environment and installs all Python dependencies.
3. **Data Acquisition:** Downloads the latest 24 hours of global event data from the GDELT project (covering all global news).
4. **Targeted Extraction & Scoring:** Calculates TF-IDF baselines and uses DeepSeek to aggressively filter the global dataset, isolating only events related to Artificial Intelligence. 
5. **Clustering & Sequencing:** Groups the isolated AI events into distinct narrative clusters and sequences them by their global and geopolitical importance.
6. **AI Enrichment:** Passes the sequenced clusters back to DeepSeek for deep geopolitical analysis and summarization according to `editorial_guidelines.md`.
7. **Report Generation:** Compiles the AI analysis into a formatted HTML briefing.
8. **Delivery:** Emails the final HTML report directly to the executive inbox.
9. **Memory Sync:** Uploads the updated SQLite database back to Google Cloud Storage so the AI remembers today's baseline for tomorrow.
