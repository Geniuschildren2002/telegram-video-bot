import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "downloads")
RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "5"))

# Vaqtinchalik fayllar papkasini yaratish
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi! .env faylini tekshiring.")
