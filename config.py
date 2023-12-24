# (c) Mr. Avishkar
import logging
import os
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s [%(pathname)s:%(lineno)d]",
    datefmt="%d-%b-%y %I:%M:%S %p"
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PYROGRAM_STRING_SESSION = os.environ.get("PYROGRAM_STRING_SESSION", "")
API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", ""))
AUTH_USERS = set(int(x) for x in os.environ.get("AUTH_USERS", "").split())
DB_URL = os.environ.get("DB_URL", "")
DB_NAME = os.environ.get("DB_NAME", "ClawBox-Bot")
BROADCAST_AS_COPY = bool(os.environ.get("BROADCAST_AS_COPY", True))
CONCURRENT_UPLOAD_LIMIT = int(os.environ.get("CONCURRENT_UPLOAD_LIMIT", 2))
ONGOING_UPLOAD_PROCESSES = {}
ONGOING_DOWNLOAD_PROCESSES = {}
