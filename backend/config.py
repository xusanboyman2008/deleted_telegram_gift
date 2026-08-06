import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Set your Telegram numeric user ID here (or via env var ADMIN_ID)
ADMIN_ID = int(os.getenv("ADMIN_ID", "6588631008"))

# ngrok / public HTTPS URL (set automatically by start.sh)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Default commission in stars added on top of gift base price
DEFAULT_COMMISSION = int(os.getenv("DEFAULT_COMMISSION", "10"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "gifts.db"))
