# (c) Mr. Avishkar

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
AUTH_USERS = config.AUTH_USERS

db = UsersDatabase(DB_URL, DB_NAME)


@Bot.on_message(filters.command("withdraw_status"))
async def withdraw_status(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id
    refresh_token = db.get_refresh_token(chat_id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)
        if len(message.command) == 1 or message.reply_to_message:
            return await message.reply(
                "Kindly send a Payout Request ID along with the command or reply /withdraw_status to any Payout Request ID to download.",
                quote=True,
            )

        req_id = (
            message.reply_to_message.text
            if message.reply_to_message
            else message.command[1:][0]
        )

        _temp = await message.reply("Fetching request details...", quote=True)

        details = await clawbox.request_status(req_id)

        await _temp.edit(f"{details.get('msg') or details['error']}.")
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
