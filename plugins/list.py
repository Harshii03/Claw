# (c) Mr. Avishkar

import hashlib

from urllib.parse import urlparse
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
LOG_CHANNEL = config.LOG_CHANNEL

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("list"))
async def clawbox_list(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    if message.chat.id == LOG_CHANNEL:
        return

    chat_id = message.from_user.id
    refresh_token = db.get_refresh_token(chat_id)

    msg = await message.reply("Getting Files List from server 🐕‍🦺...", quote=True)

    if refresh_token:
        clawbox = ClawBox(refresh_token)
        files = await clawbox.listFiles()

        if (not isinstance(files, list)) and files.get("error"):
            return await msg.edit(files.get("error"))

        btns = []

        for file in files[:6]:
            if file.get("is_uploading") is True:
                continue

            md5 = hashlib.md5(file['FileID'].encode()).hexdigest()
            btns.append(
                [
                    InlineKeyboardButton(
                        f"{file['Original_File_Name']}",
                        callback_data=f"v_{md5}",
                    ),
                    InlineKeyboardButton(
                        "Share URL",
                        url=f"https://clawbox.in/s/{file['FileID']}",
                    ),
                    InlineKeyboardButton(
                        f"🗑️",
                        callback_data=f"d_{md5}",
                    ),
                ]
            )
        btns.append(
            [
                InlineKeyboardButton(
                    f"[1/{int(len(files)/6)+1 if len(files) > 6 else 1}]",
                    callback_data="noop"
                )
            ]
        )

        if len(files) > 6:
            btns.append(
                [
                    InlineKeyboardButton(
                        f"⏭️ Next",
                        callback_data="list_1",
                    )
                ]
            )
        
        await msg.edit(f"Found **{len(files)} files** in your ClawBox account.", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
