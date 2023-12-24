# (c) Mr. Avishkar
from pyrogram import Client
import config
CLAWBOXUB = Client(
    "ClawBox-UserBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.PYROGRAM_STRING_SESSION,
    sleep_threshold=10,
    workers=355,
    max_concurrent_transmissions=15,
)

