import os
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY"
)

WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET"
)


# ==================================================
# LIBRETRANSLATE - OPTIONAL
# ==================================================

LIBRETRANSLATE_URL = os.getenv(
    "LIBRETRANSLATE_URL",
    ""
).rstrip("/")

LIBRETRANSLATE_API_KEY = os.getenv(
    "LIBRETRANSLATE_API_KEY",
    ""
)


if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN was not found!"
    )

if not SUPABASE_URL:
    raise ValueError(
        "SUPABASE_URL was not found!"
    )

if not SUPABASE_SECRET_KEY:
    raise ValueError(
        "SUPABASE_SECRET_KEY was not found!"
    )

if not WEBHOOK_SECRET:
    raise ValueError(
        "WEBHOOK_SECRET was not found!"
    )