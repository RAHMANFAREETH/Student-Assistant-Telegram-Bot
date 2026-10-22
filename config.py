import os
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# BOT TOKEN
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN was not found!")


# ==========================================
# DATABASE LOCATION
# ==========================================

DATA_DIR = os.getenv(
    "RAILWAY_VOLUME_MOUNT_PATH",
    "."
)

DB_NAME = os.path.join(
    DATA_DIR,
    "student_bot.db"
)