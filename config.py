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
    "DATA_DIR",
    "."
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

DB_NAME = os.path.join(
    DATA_DIR,
    "student_bot.db"
)