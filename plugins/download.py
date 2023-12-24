# (c) Mr. Avishkar

import os
import shutil
import time
from urllib.parse import urlparse

import aiofiles
import ffmpeg
import httpx
import magic
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ChatAction, ParseMode
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from helpers.progress import TimeFormatter, humanbytes, progress_for_pyrogram
from helpers.clawbox import ClawBox
from utils.convertors import convert_timestamp_to_datetime
from utils.Nekmo_ffmpeg import get_thumbnail
from utils.validators import is_clawbox_url, is_url
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
LOG_CHANNEL = config.LOG_CHANNEL
ONGOING_DOWNLOAD_PROCESSES = config.ONGOING_DOWNLOAD_PROCESSES

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("download"))
async def download(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id

    if message.chat.id == LOG_CHANNEL:
        return

    refresh_token = db.get_refresh_token(chat_id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)
        if len(message.command) == 1 or message.reply_to_message:
            return await message.reply(
                "Kindly send a ClawBox link along with the command or reply /download to any ClawBox link to download.",
                quote=True,
            )

        data = await bot.get_me()
        BOT_USERNAME = data.username

        link = (
            message.reply_to_message.text
            if message.reply_to_message
            else message.command[1:][0]
        )
        is_valid = is_url(link) and is_clawbox_url(link)

        if is_valid != True:
            return await message.reply(
                f"Kindly send a ClawBox valid link along with the command or reply /download to any ClawBox link to download as `{link}` is not a valid ClawBox url.",
                quote=True,
            )

        if (
            ONGOING_DOWNLOAD_PROCESSES.get(chat_id, 0)
            >= 2
        ):
            return await message.reply(
                f"Sorry but your concurrent Download quota (**2 files**) exceeded. Kindly wait for the older downloads to be completed or if you think it's an mistake then kindly contact my support group.",
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

        ONGOING_DOWNLOAD_PROCESSES[chat_id] = ONGOING_DOWNLOAD_PROCESSES.get(chat_id, 0) + 1

        status_msg = await message.reply(
            f"Getting file details 📦...", parse_mode=ParseMode.MARKDOWN, quote=True
        )

        clawbox = ClawBox()
        
        res = await clawbox.fileDetails(urlparse(link).path.rstrip("/").split("/")[-1], public=True)

        if res.get("error"):
            return await status_msg.edit("No file found might me file deleted or the link is invalid.")

        if int(res["File_size"]) >= 2097152000 and bot.userbot is None:
            ONGOING_DOWNLOAD_PROCESSES[chat_id] = (
                ONGOING_DOWNLOAD_PROCESSES.get(chat_id) - 1
            )
            return await status_msg.edit(
                f"Sorry man,\n\nBut currently I am unable to upload files more than `{humanbytes(2097152000)}`. Usually it already get's fixed. But still facing the same issue from long period of time. Then kindly contact my Support Group @ClawBoxSupport.",
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
            )

        dl_url = f"https://{clawbox.CLAWBOX_API_DOMAIN}/api/file/get/d/{res['FileID']}/"

        await status_msg.edit(
            f"Starting download from ClawBox 📦...", parse_mode=ParseMode.MARKDOWN
        )

        down_start = time.time()
        username = (await bot.get_me()).username

        suid = str(time.time()).replace(".", "")
        DOWNLOADS_FOLDER = f"./DOWNLOADS/{suid}/"
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

        file_location = (
            f"{DOWNLOADS_FOLDER}[Downloaded By @{username}]_{res['Original_File_Name']}"
        )

        HEADERS = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9"
        }

        async with aiofiles.open(file_location, mode="wb") as file:
            async with clawbox.session.stream(
                "GET",
                dl_url,
                headers=HEADERS,
                timeout=httpx.Timeout(180.0),
                follow_redirects=True,
            ) as response:
                total = int(res["File_size"])
                async for chunk in response.aiter_bytes():
                    await file.write(chunk)
                    await progress_for_pyrogram(
                        response.num_bytes_downloaded,
                        total,
                        "**Downloading from ClawBox 📦...**",
                        status_msg,
                        down_start,
                        bot,
                        chatAction=ChatAction.PLAYING,
                    )

        upload_start = time.time()

        mime = magic.Magic(mime=True)
        isVideo = False
        filename = mime.from_file(file_location)
        if filename.find("video") != -1:
            isVideo = True

        CAPTION = f"**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n\n**📁 File Name:** `{res['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(res['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(res['Modified_At'])}`\n**🔗 URL:** {link}"
        if isVideo:
            metadata = ffmpeg.probe(file_location)["streams"]

            height, width, duration = 0, 0, 0
            for meta in metadata:
                if not height:
                    height = int(meta.get("height", 0))
                if not width:
                    width = int(meta.get("width", 0))
                if not duration:
                    duration = int(int(meta.get("duration_ts", 0)) / 1000)

            metadata = extractMetadata(createParser(file_location))
            try:
                if metadata.has("duration"):
                    duration = metadata.get("duration").seconds
            except:
                pass

            thumbnail = await get_thumbnail(duration, file_location)

            if int(res["File_size"]) >= 2097152000:
                __downloaded = await bot.userbot.send_video(
                    LOG_CHANNEL,
                    video=file_location,
                    caption=CAPTION,
                    duration=duration,
                    height=height,
                    width=width,
                    thumb=thumbnail,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "📥Uploading...",
                        status_msg,
                        upload_start,
                        bot,
                        ChatAction.UPLOAD_VIDEO,
                    ),
                )

                _downloaded = await bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=__downloaded.chat.id,
                    message_id=__downloaded.id,
                    reply_to_message_id=message.id,
                    caption=CAPTION,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    f"🤖 Uploaded By @{BOT_USERNAME}",
                                    url=f"https://t.me/{BOT_USERNAME}",
                                )
                            ]
                        ]
                    ),
                )

                try:
                    await __downloaded.delete(True)
                except:
                    pass

            else:
                _downloaded = await message.reply_video(
                    video=file_location,
                    caption=CAPTION,
                    duration=duration,
                    height=height,
                    width=width,
                    thumb=thumbnail,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "📥Uploading...",
                        status_msg,
                        upload_start,
                        bot,
                        ChatAction.UPLOAD_VIDEO,
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    f"🤖 Uploaded By @{BOT_USERNAME}",
                                    url=f"https://t.me/{BOT_USERNAME}",
                                )
                            ]
                        ]
                    ),
                    quote=True,
                )
        else:
            if int(res["File_size"]) >= 2097152000:
                __downloaded = await bot.userbot.send_document(
                    LOG_CHANNEL,
                    document=file_location,
                    caption=CAPTION,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "📥Uploading...",
                        status_msg,
                        upload_start,
                        bot,
                        ChatAction.UPLOAD_DOCUMENT,
                    ),
                )

                _downloaded = await bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=__downloaded.chat.id,
                    message_id=__downloaded.id,
                    reply_to_message_id=message.id,
                    caption=CAPTION,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    f"🤖 Uploaded By @{BOT_USERNAME}",
                                    url=f"https://t.me/{BOT_USERNAME}",
                                )
                            ]
                        ]
                    ),
                )

                try:
                    await __downloaded.delete(True)
                except:
                    pass

            else:
                _downloaded = await message.reply_document(
                    document=file_location,
                    caption=CAPTION,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "📥Uploading...",
                        status_msg,
                        upload_start,
                        bot,
                        ChatAction.UPLOAD_DOCUMENT,
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    f"🤖 Uploaded By @{BOT_USERNAME}",
                                    url=f"https://t.me/{BOT_USERNAME}",
                                )
                            ]
                        ]
                    ),
                    quote=True,
                )

        try:
            await _downloaded.edit_caption(
                f"**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n\n**📁 File Name:** `{res['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(res['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(res['Modified_At'])}`\n**🔗 URL:** {link}",
                reply_markup=_downloaded.reply_markup,
            )
        except MessageNotModified:
            pass

        ONGOING_DOWNLOAD_PROCESSES[chat_id] = ONGOING_DOWNLOAD_PROCESSES.get(chat_id) - 1

        if LOG_CHANNEL:
            _forwared = await _downloaded.forward(LOG_CHANNEL)
            user_mention = message.from_user.mention(
                f"{message.from_user.first_name}{' '+message.from_user.last_name if message.from_user.last_name else ''}",
                style=ParseMode.MARKDOWN,
            )
            await _forwared.reply(
                f"#NewFileDownloaded:\n\nUser {user_mention} (`{message.from_user.id}`) downloaded a file from ClawBox using @{BOT_USERNAME} !!\n\n**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n**📁 File Name:** `{res['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(res['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(res['Modified_At'])}`\n**🔗 URL:** {link}",
                parse_mode=ParseMode.MARKDOWN,
                quote=True,
            )

        try:
            shutil.rmtree(os.path.dirname(file_location), ignore_errors=True)
        except:
            pass
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
