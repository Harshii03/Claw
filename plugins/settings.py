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

@Bot.on_message(filters.command("settings"))
async def opensettings(bot: Bot, cmd: Message):
    await handle_user_status(bot, cmd)
    user_id = cmd.from_user.id
    await cmd.reply_text(
        f"`Here You Can Set Your Settings:`\n\nSuccessfully setted notifications to **{db.get_notif(user_id)}**",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"NOTIFICATION  {'🔔' if ((db.get_notif(user_id)) is True) else '🔕'}",
                        callback_data="notification",
                    )
                ],
                [InlineKeyboardButton("❎", callback_data="closeMeh")],
            ]
        ),
        quote=True,
    )
