# (c) Mr. Avishkar

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.types import Message

import config
from handlers.check_user import handle_user_status

@Bot.on_message(filters.service & filters.group)
async def service_message(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    if message.chat.id == config.LOG_CHANNEL:
        return await message.delete(True)
