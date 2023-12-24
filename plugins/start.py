# (c) Mr. Avishkar

import base64
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("start") & filters.private)
async def startprivate(client: Bot, message: Message):
    await handle_user_status(client, message)
    if len(message.command) != 1:
        data = message.command[1]
        encoded = base64.b64decode(data)
        return await message.reply(f"Kindly send `/{encoded.decode()}`")

    joinButton = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Updates Channel 📡", url="https://t.me/ClawBox"
                )
            ]
        ]
    )

    refresh_token = db.get_refresh_token(message.from_user.id)
    if refresh_token:
        welcomed = "Login Successful!! Start Uploading ❤️❤️"
    else:
        welcomed = f"""Hi <b>{message.from_user.mention}</b>! Welcome to ClawBox Bot You, i can do many things to make your work easy. i am the 🧜‍♂️God Mod Bot of ClawBox, Ultra powerful, Easy To Use, Low Chances of Fail💪

**👑Bot Features**

**-** Upload Video File

Upload direct or forward video file and get your ClawBox link here.

**-** Remote URL ( Direct Download Link )

I can upload any video file using remote link of download url.

**-** Copy Any ClawBox Video in 1 click

**-** Copy Any Telegram Videos

You can forward any telegram video file to me and you will get your Clawbox Url of that video directly from here.
"""
    await message.reply_text(welcomed, reply_markup=joinButton, quote=True)
