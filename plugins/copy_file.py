# (c) Mr. Avishkar

from urllib.parse import urlparse
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from helpers.progress import humanbytes
from utils.convertors import convert_timestamp_to_datetime
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
LOG_CHANNEL = config.LOG_CHANNEL

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("copy"))
async def clawbox_copy(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    if message.chat.id == LOG_CHANNEL:
        return

    chat_id = message.from_user.id
    links = message.command[1:]

    if not links:
        return await message.reply("Kindly send me links to copy.")

    refresh_token = db.get_refresh_token(chat_id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)

        for LINK in links:
            msg = await message.reply(f"Copying {LINK}...", quote=True)
            details, newURL = await clawbox.copy(urlparse(LINK).path.rstrip("/").split("/")[-1])
            if details:
                await msg.edit(
                    f"**Successfully copied:**\n\n**📁 File Name:** `{details['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(details['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(details['Modified_At'])}`\n**🔗 URL:** {LINK}\n**New URL:** {newURL}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                if LOG_CHANNEL:
                    data = await bot.get_me()
                    BOT_USERNAME = data.username
                    user_mention = message.from_user.mention(
                        f"{message.from_user.first_name}{' '+message.from_user.last_name if message.from_user.last_name else ''}",
                        style=ParseMode.MARKDOWN,
                    )

                    await bot.send_message(
                        LOG_CHANNEL,
                        f"#NewLinkConverted: \n\nUser {user_mention}(`{message.from_user.id}`) used @{BOT_USERNAME} !!\n\n**📁 File Name:** `{details['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(details['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(details['Modified_At'])}`\n**🔗 URL:** {LINK}\n**New URL:** {newURL}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
            else:
                await msg.edit(f"`{newURL}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
