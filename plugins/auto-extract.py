# (c) Mr. Avishkar

from urllib.parse import urlparse
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
from pyrogram.types import Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from utils.extractors import extract_links
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(
    filters.private
    & ~filters.regex(pattern="^/")
    & filters.regex(
        pattern=r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
)
async def auto_copy(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id
    refresh_token = db.get_refresh_token(chat_id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)

        if message.media:
            oldMessage = message.caption.markdown
            links = extract_links(message.caption)
        else:
            oldMessage = message.text.markdown
            links = extract_links(message.text)

        error = 0
        success = 0
        duplicate = 0
        successLinks = []
        erroredLinks = []
        _temp = await message.reply(
            f"Found `{len(links)}` links.\n\n**📝 Files copy stats:**\n\n**Successfully:** `{success}/{len(links)}`\n**Errors:** `{error}/{len(links)}`\n**Replication:** `{duplicate}/{len(links)}`",
            quote=True,
        )

        for link in links:
            try:
                if link not in successLinks:
                    details, newURL = await clawbox.copy(urlparse(link).path.rstrip("/").split("/")[-1])
                    if isinstance(details, dict):
                        oldMessage = oldMessage.replace(link, newURL)
                        success += 1
                        successLinks.append(link)
                    else:
                        error += 1
                        erroredLinks.append({"link": link, "error": newURL})
                else:
                    duplicate += 1
            except:
                error += 1
                erroredLinks.append(
                    {
                        "link": link,
                        "error": "Something unexpected. Might not an valid ClawBox URL.",
                    }
                )

            await _temp.edit(
                f"Found `{len(links)}` links.\n\n**📝 Files copy stats:**\n\n**Successfully:** `{success}/{len(links)}`\n**Errors:** `{error}/{len(links)}`\n**Replication:** `{duplicate}/{len(links)}`"
            )

        stats = (
            f"Found `{len(links)}` links.\n\n"
            f"**📝 Files copy stats:**\n\n"
            f"**Successfully:** `{success}/{len(links)}`\n"
            f"**Errors:** `{error}/{len(links)}`\n"
            f"**Replication:** `{duplicate}/{len(links)}`\n\n"
        )

        if error > 0:
            stats += "**🌋 Errored Links:**\n\n"
            for index, errorLink in enumerate(erroredLinks):
                stats += f"**{index+1}.** {errorLink['link']}\nError: `{errorLink['error']}`\n\n"

        try:
            await _temp.edit(stats)
        except MessageNotModified:
            pass

        if success != 0:
            if message.media:
                await message.copy(
                    message.from_user.id, caption=oldMessage, reply_to_message_id=message.id
                )
            else:
                await message.reply(oldMessage, quote=True)
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
