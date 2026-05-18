# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Grab ALL the secrets from the Docker environment
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("MY_SECRET_EMAIL")

def send_email():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 11: Emailing Report...")

    if not APP_PASSWORD or not RECEIVER_EMAIL or not SENDER_EMAIL:
        print("❌ ERROR: Missing email credentials in environment variables.")
        return
