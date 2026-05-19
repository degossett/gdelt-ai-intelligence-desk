import os
import smtplib
import glob
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "topic_filter.md")

# Grab ALL the secrets from the Docker environment
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("MY_SECRET_EMAIL")

def send_email():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 11: Emailing Report...")

    if not APP_PASSWORD or not RECEIVER_EMAIL or not SENDER_EMAIL:
        print("❌ ERROR: Missing email credentials in environment variables.")
        return

    # --- DYNAMIC TOPIC EXTRACTION ---
    topic_name = "Global Events" # Default fallback
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith("TOPIC:"):
                topic_name = first_line.replace("TOPIC:", "").strip()

    # 1. Find today's HTML report in the main folder
    search_pattern = os.path.join(BASE_DIR, "GDELT_AI_Briefing_*.html")
    html_files = glob.glob(search_pattern)
    
    if not html_files:
        print("❌ ERROR: Could not find any HTML briefing files to email.")
        return
        
    # Get the most recently created HTML file
    latest_html_file = max(html_files, key=os.path.getctime)
    print(f"📄 Found report: {latest_html_file}")

    # 2. Read the HTML content
    with open(latest_html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 3. Build the Email (GLOBE REMOVED!)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"GDELT Intelligence Briefing: {topic_name} - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # Attach the HTML directly to the email body!
    part = MIMEText(html_content, 'html')
    msg.attach(part)

    # 4. Send the Email via Gmail SMTP
    try:
        print("🚀 Connecting to Gmail SMTP server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print("✅ Success! The AI Briefing was sent to your inbox.")
    except Exception as e:
        print(f"❌ ERROR sending email: {e}")

if __name__ == '__main__':
    send_email()
