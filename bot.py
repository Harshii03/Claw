import logging
import shutil
import time
import pyromod
from pyrogram import Client, idle
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated
import config
from handlers.database import UsersDatabase
from user_client import CLAWBOXUB
BOT_USERNAME = ""
DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
db = UsersDatabase(DB_URL, DB_NAME)
class PyromodConfig:
    timeout_handler = None
    stopped_handler = None
    throw_exceptions = True
    unallowed_click_alert = True
    unallowed_click_alert_text = (
        f"[@{BOT_USERNAME}] You're not expected to click this button."
    )
class Bot(Client):
    def __init__(self):
        super().__init__(
            "ClawBox-Bot",
            bot_token=config.BOT_TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            plugins={"root": "plugins"},
            workers=355,
            max_concurrent_transmissions=15,
        )
        self.stop_check = False
    async def start(self):
        global BOT_USERNAME
        await super().start()
        self.userbot = None
        __USERBOT_STOP_REASON = None
        if config.PYROGRAM_STRING_SESSION:
            logging.info("Found User String. Start the UserBot.")
            try:
                await CLAWBOXUB.start()
                self.userbot = CLAWBOXUB
                usr_bot_me = await self.userbot.get_me()
                USERBOT_USERNAME = usr_bot_me.username
                if usr_bot_me.is_premium:
                    logging.info(
                        f"@{USERBOT_USERNAME} UserBot connected to the Servers successfully."
                    )
                else:
                    self.userbot = None
                    __USERBOT_STOP_REASON = f"@{USERBOT_USERNAME} UserBot hasn't have the Telegram Premium so, connecting is useless. So, disconnected."
                    logging.critical(__USERBOT_STOP_REASON)
                    await self.userbot.stop()
            except AuthKeyDuplicated:
                __USERBOT_STOP_REASON = (
                    "Userbot's string session expired. Kindly regenerate a new one."
                )
                logging.critical(__USERBOT_STOP_REASON)
            except Exception:
                __USERBOT_STOP_REASON = f"Userbot's string session expired. Kindly regenerate a new one.\n\nError:\n{traceback.format_exc()}"
                logging.critical(
                    "Something went wrong while connecting with the UserBot."
                )
        else:
            __USERBOT_STOP_REASON = (
                "String session not found, kindly update in in ENVs."
            )
            logging.critical(__USERBOT_STOP_REASON)
        self.bot_me = await self.get_me()
        self.uptime = time.time()
        BOT_USERNAME = self.bot_me.username
        logging.info(f"@{self.bot_me.username} Bot Running..!")
        await idle()
    async def stop(self, *args):
        self.stop_check = True
        await super().stop()
        try:
            shutil.rmtree("./DOWNLOADS")
        except FileNotFoundError:
            pass
        logging.warn("Bot stopped.")
      
