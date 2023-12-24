# (c) Mr. Avishkar

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("about"))
async def about(bot: Bot, cmd: Message):
    await handle_user_status(bot, cmd)
    about_txt = (
        f"I am just a simple ClawBox Bot.\n\n"
        "⦿ Send me any File to upload to your ClawBox account.\n"
        "⦿ Send me any message containing ClawBox links to copy all of the ClawBox links to your account and replace the old links with the new one.\n"
        "⦿ Send me a ClawBox link with `\copy` command and get your Embend Link.\n"
        "**Eg.** `\copy https://clawboxapp.com/s/xxxxxxxxxxxxxx`\n\n"
        "⦿ Send me a ClawBox link with `\download` command and upload the file to Telegram.\n"
        "**Eg.** `\download https://clawboxapp.com/s/xxxxxxxxxxxxxx`\n\n"
        "This bot is a part of 🥳 @ClawBox community made by @Mr_Avishkar."
    )
    await cmd.reply_text(
        about_txt,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Community 🫴", url="https://t.me/ClawBox")]]
        ),
        quote=True,
    )
