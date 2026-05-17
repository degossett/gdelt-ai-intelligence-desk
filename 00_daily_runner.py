import os
import subprocess
import time
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# List your scripts in the exact order they must run
# Update these names if your actual file names differ slightly!
PIPELINE_SCRIPTS = [
    "01_download_gdelt.py",       # Assuming this is your Script 1 name
    "02_build_cluster_counts.py",
    "03_build_corpus.py",
    "03a_dynamic_stopwords.py",
    "04_build_cluster_idf.py", # Our new Daily Counter
    "05_build_rolling_idf.py",     # Our Rolling Baseline Math
    "06_calculate_daily_tfidf.py",
    "07_score_headlines.py",
    "08_ai_enrichment.py",
    "09_ai_cluster_editor.py",
    "10_build_ai_report.py"
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
