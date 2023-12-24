# (c) Mr. Avishkar

import os
import shutil
import time

import magic
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from helpers.downloader import download_file
from helpers.progress import TimeFormatter, progress_for_pyrogram
from helpers.clawbox import ClawBox
from utils.file_size import human_size
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
LOG_CHANNEL = config.LOG_CHANNEL
CONCURRENT_UPLOAD_LIMIT = config.CONCURRENT_UPLOAD_LIMIT
ONGOING_UPLOAD_PROCESSES = config.ONGOING_UPLOAD_PROCESSES

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(
    filters.video
    | filters.document
    | filters.audio
    | filters.photo
    | filters.voice
    | filters.video_note
    | filters.animation
)
async def upload(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    if message.chat.id == LOG_CHANNEL:
        return

    chat_id = message.from_user.id

    if (
        ONGOING_UPLOAD_PROCESSES.get(chat_id, 0)
        >= 2
    ):
        return await message.reply(
            f"Sorry but your concurrent Upload quota (**2 files**) exceeded. Kindly wait for the older uploads to be completed or if you think it's an mistake then kindly contact my support group.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Support Group 🐕‍🦺",
                            url="https://t.me/ClawBoxSupport",
                        )
                    ]
                ]
            ),
            quote=True,
        )

    refresh_token = db.get_refresh_token(chat_id)
    if refresh_token:
        ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id, 0) + 1

        status_msg = await message.reply("Downloading File ⬇️", quote=True)

        down_start = time.time()
        file_path = await download_file(
            bot, message, status_msg, False
        )
        down_end = time.time()

        clawbox = ClawBox(refresh_token)

        username = (await bot.get_me()).username
        file_name = os.path.basename(file_path)

        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)

        total_size = os.stat(file_path).st_size

        await clawbox.init_upload(file_name, total_size, mime_type)

        await status_msg.edit(
            f"Starting upload to ClawBox 📦...", parse_mode=ParseMode.MARKDOWN
        )
        start = time.time()
        with open(file_path, "rb") as file:
            total_uploaded = 0
            while True:
                bytes = file.read(5242880)
                total_uploaded += len(bytes)
                if not bytes:
                    break
                await clawbox.upload_bytes(bytes)
                await progress_for_pyrogram(
                    total_uploaded,
                    total_size,
                    "**Uploading to ClawBox 📦...**",
                    status_msg,
                    start,
                    bot,
                )

        fileID = await clawbox.finalize_upload()

        file_details = await clawbox.fileDetails(fileID['id'], public=True)

        await status_msg.edit(
            f"**Successfully uploaded:**\n\n**Downloaded in:** `{TimeFormatter(milliseconds=round(down_end-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-start)*1000)}`\n**FileName:** `{file_details['Original_File_Name']}`\n**File Size:** `{human_size(file_details['File_size'])}`\n**Share URL:** https://www.clawbox.in/s/{file_details['FileID']}",
            parse_mode=ParseMode.MARKDOWN,
        )
        ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id) - 1

        if LOG_CHANNEL:
            data = await bot.get_me()
            BOT_USERNAME = data.username
            _forwared = await message.forward(LOG_CHANNEL)
            user_mention = message.from_user.mention(
                f"{message.from_user.first_name}{' '+message.from_user.last_name if message.from_user.last_name else ''}",
                style=ParseMode.MARKDOWN,
            )
            await _forwared.reply(
                f"#NewFileUploaded:\n\nUser {user_mention} (`{message.from_user.id}`) uploaded file to ClawBox using @{BOT_USERNAME} !!\n\n**Downloaded in:** `{TimeFormatter(milliseconds=round(down_end-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-start)*1000)}`\n**FileName:** `{file_details['Original_File_Name']}`\n**File Size:** `{human_size(file_details['File_size'])}`\n**Share URL:** https://www.clawbox.in/s/{file_details['FileID']}",
                parse_mode=ParseMode.MARKDOWN,
                quote=True,
            )
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )

    try:
        shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
    except:
        pass
