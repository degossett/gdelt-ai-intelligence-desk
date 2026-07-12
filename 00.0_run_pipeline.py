import os
import subprocess
import time
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))[cite: 20]

# List your scripts in the exact order they must run
# Updated to match the new XX.Y naming convention!
PIPELINE_SCRIPTS = [
        "00.1_idempotency_shield.py",
        "01.0_download_gdelt.py",
        "02.0_build_cluster_counts.py",
        "03.0_build_corpus.py",
        "03.1_dynamic_stopwords.py",
        "04.0_build_cluster_idf.py",
        "05.0_build_rolling_idf.py",
        "06.0_calculate_daily_tfidf.py",
        "07.0_score_headlines.py",
        "08.0_anti_plagiarism_filter.py",  # The New Bouncer
        "09.0_ai_enrichment.py",
        "10.0_ai_cluster_editor.py",
        "11.0_build_ai_report.py",
        "12.0_email_report.py",
        "13.0_intelligence_stats.py",      # Stats run FIRST while data is hot
        "14.0_database_cleanup.py"         # Cleanup runs LAST before uploading
    ]

def run_pipeline():
    print(f"==================================================")[cite: 20]
    print(f"🚀 STARTING GDELT DAILY PIPELINE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")[cite: 20]
    print(f"==================================================\n")[cite: 20]
    
    total_start_time = time.time()[cite: 20]

    for script_name in PIPELINE_SCRIPTS:[cite: 20]
        script_path = os.path.join(BASE_DIR, script_name)[cite: 20]
        
        if not os.path.exists(script_path):[cite: 20]
            print(f"❌ ERROR: Cannot find script: {script_path}")[cite: 20]
            print("Pipeline aborted.")[cite: 20]
            return[cite: 20]

        print(f"▶️ RUNNING: {script_name} ...")[cite: 20]
        script_start = time.time()[cite: 20]
        
        try:
            # We use subprocess to run the script just like you do in the terminal[cite: 20]
            # check=True means if the script crashes, it will raise an error here and stop the pipeline[cite: 20]
            subprocess.run(["python", script_path], check=True)[cite: 20]
            
            script_time = time.time() - script_start[cite: 20]
            print(f"✅ SUCCESS: {script_name} completed in {script_time:.2f} seconds.\n")[cite: 20]
            
        except subprocess.CalledProcessError as e:[cite: 20]
            print(f"\n❌ PIPELINE FAILED AT: {script_name}")[cite: 20]
            print(f"Error Details: {e}")[cite: 20]
            print("Aborting remaining scripts.")[cite: 20]
            return[cite: 20]
            
    total_time = time.time() - total_start_time[cite: 20]
    print(f"==================================================")[cite: 20]
    print(f"🎉 PIPELINE COMPLETE! Total time: {total_time:.2f} seconds.")[cite: 20]
    print(f"==================================================")[cite: 20]

if __name__ == '__main__':
    run_pipeline()[cite: 20]
