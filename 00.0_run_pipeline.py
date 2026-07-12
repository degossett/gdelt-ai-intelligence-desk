import os
import subprocess
import time
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    print(f"==================================================")
    print(f"🚀 STARTING GDELT DAILY PIPELINE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"==================================================\n")
    
    total_start_time = time.time()

    for script_name in PIPELINE_SCRIPTS:
        script_path = os.path.join(BASE_DIR, script_name)
        
        if not os.path.exists(script_path):
            print(f"❌ ERROR: Cannot find script: {script_path}")
            print("Pipeline aborted.")
            return

        print(f"▶️ RUNNING: {script_name} ...")
        script_start = time.time()
        
        try:
            # We use subprocess to run the script just like you do in the terminal
            # check=True means if the script crashes, it will raise an error here and stop the pipeline
            subprocess.run(["python", script_path], check=True)
            
            script_time = time.time() - script_start
            print(f"✅ SUCCESS: {script_name} completed in {script_time:.2f} seconds.\n")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ PIPELINE FAILED AT: {script_name}")
            print(f"Error Details: {e}")
            print("Aborting remaining scripts.")
            return
            
    total_time = time.time() - total_start_time
    print(f"==================================================")
    print(f"🎉 PIPELINE COMPLETE! Total time: {total_time:.2f} seconds.")
    print(f"==================================================")

if __name__ == '__main__':
    run_pipeline()
