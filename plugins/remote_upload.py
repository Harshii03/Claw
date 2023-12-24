# (c) Mr. Avishkar

import os
import re
import shutil
import time
from urllib.parse import urlparse, unquote
import aiofiles
import httpx

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ChatAction, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from helpers.gdrive import FileURLRetrievalError, GDrive
from helpers.progress import TimeFormatter, progress_for_pyrogram
from helpers.clawbox import ClawBox
from helpers.terabox import TeraBox
from utils.clean_filename import cleanFileName
from utils.file_size import human_size
from utils.validators import is_url
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
LOG_CHANNEL = config.LOG_CHANNEL
CONCURRENT_UPLOAD_LIMIT = config.CONCURRENT_UPLOAD_LIMIT
ONGOING_UPLOAD_PROCESSES = config.ONGOING_UPLOAD_PROCESSES

db = UsersDatabase(DB_URL, DB_NAME)


@Bot.on_message(filters.command("remote"))
async def remote_upload(bot: Bot, message: Message):
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
        clawbox = ClawBox(refresh_token)

        if len(message.command) == 1 or message.reply_to_message:
            return await message.reply(
                "Kindly send a direct link along with the command or reply /remote to any direct link to upload to ClawBox.",
                quote=True,
            )

        link = (
            message.reply_to_message.text
            if message.reply_to_message
            else message.command[1:][0]
        )

        if not is_url(link):
            return await message.reply(
                f"Kindly send a valid link along with the command or reply /remote to any link for remote upload as `{link}` is not a valid Url.",
                quote=True,
            )

        ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id, 0) + 1

        status_msg = await message.reply("Checking Link ⬇️", quote=True)

        down_start = time.time()

        suid = str(time.time()).replace(".", "")
        DOWNLOADS_FOLDER = f"./DOWNLOADS/{suid}/"
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        
        gdrive = GDrive()
        terabox = TeraBox()

        is_gdrive = False
        is_terabox = False

        HEADERS = {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Language": "en-US,en;q=0.9",
            "Host": f"{urlparse(link).netloc.split('@')[-1]}",
            "User-Agent": clawbox.user_agent,
        }

        if "drive.google.com" in link:
            is_gdrive = True
            try:
                details = await gdrive.getDetails(link, fuzzy=True)
                fname = details['filename']
                file_size = details['size']
                file_type = details['mimetype']
            except FileURLRetrievalError as e:
                ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id) - 1
                return await status_msg.edit(
                    e, parse_mode=ParseMode.MARKDOWN
                )
        elif terabox.is_terabox_url(link):
            await terabox.init()
            is_terabox = True
            terabox_res = await terabox.get_download_url(link)
            if "list" in terabox_res:
                terabox_res = terabox_res["list"][0]

                file_size = terabox_res["size"]
                fname = terabox_res['server_filename']
                link = unquote(terabox_res["dlink"])

                response = await terabox.session.head(
                    link,
                    headers=terabox.headers,
                    cookies=terabox.cookies,
                    timeout=httpx.Timeout(180.0),
                    follow_redirects=True,
                )

                file_type = response.headers.get("content-type")
            else:
                ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id) - 1
                return await status_msg.edit(
                    "Invalid Terabox url.\n\nIf you think it's an mistake then kindly contact my support group.",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            try:
                response = await clawbox.session.head(
                    link,
                    headers=HEADERS,
                    timeout=httpx.Timeout(180.0),
                    follow_redirects=True,
                )
            except:
                ONGOING_UPLOAD_PROCESSES[chat_id] = ONGOING_UPLOAD_PROCESSES.get(chat_id) - 1
                return await status_msg.edit(
                    f"**Invalid URL..**", parse_mode=ParseMode.MARKDOWN
                )

            fname = ''
            try:
                if "Content-Disposition" in response.headers.keys():
                    fname = re.findall("filename=(.+)", response.headers["Content-Disposition"])[0]
                elif "content-disposition" in response.headers.keys():
                    fname = re.findall("filename=(.+)", response.headers["content-disposition"])[0]
                else:
                    fname = unquote(urlparse(link).path.split("/")[-1])
            except:
                fname = unquote(urlparse(link).path.split("/")[-1])

            file_size = int(response.headers.get("content-length", 0))

            file_type = response.headers.get("content-type")

        fname = cleanFileName(fname)
        
        file_location = (
            f"{DOWNLOADS_FOLDER}{fname}"
        )
        _, fileID = await clawbox.init_upload(fname, file_size, file_type, is_remote_upload=True)

        await message.reply(
            f"**Share URL:** https://www.clawbox.in/s/{fileID}", parse_mode=ParseMode.MARKDOWN, quote=True
        )
        
        await status_msg.edit(
            f"Starting download...", parse_mode=ParseMode.MARKDOWN
        )

        if is_gdrive:
            file_location = await gdrive.download(
                link,
                output=file_location,
                fuzzy=True,
                progress=progress_for_pyrogram,
                progress_args=(
                    "**Downloading from GDrive 📦...**",
                    status_msg,
                    down_start,
                    bot,
                    ChatAction.PLAYING,
                )
            )
        elif is_terabox:
            async with aiofiles.open(file_location, mode="wb") as file:
                async with terabox.session.stream(
                    "GET",
                    link,
                    headers=terabox.headers,
                    cookies=terabox.cookies,
                    timeout=httpx.Timeout(180.0),
                    follow_redirects=True,
                ) as response:
                    total = int(response.headers["Content-Length"])
                    async for chunk in response.aiter_bytes():
                        await file.write(chunk)
                        await progress_for_pyrogram(
                            response.num_bytes_downloaded,
                            total,
                            "**Downloading from TeraBox 📦...**",
                            status_msg,
                            down_start,
                            bot,
                            chatAction=ChatAction.PLAYING,
                        )
        else:
            async with aiofiles.open(file_location, mode="wb") as file:
                async with clawbox.session.stream(
                    "GET",
                    link,
                    headers=HEADERS,
                    timeout=httpx.Timeout(180.0),
                    follow_redirects=True,
                ) as response:
                    total = int(response.headers["Content-Length"])
                    async for chunk in response.aiter_bytes():
                        await file.write(chunk)
                        await progress_for_pyrogram(
                            response.num_bytes_downloaded,
                            total,
                            "**Downloading from Remote Server 📦...**",
                            status_msg,
                            down_start,
                            bot,
                            chatAction=ChatAction.PLAYING,
                        )

        down_end = time.time()
        total_size = os.stat(file_location).st_size

        await status_msg.edit(
            f"Starting upload to ClawBox 📦...", parse_mode=ParseMode.MARKDOWN
        )

        start = time.time()
        with open(file_location, "rb") as file:
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

        fileID = await clawbox.finalize_upload(is_remote_upload=True)

        if file_size != total_size:
            await clawbox.updateDetails(fileID['id'], newFileSize=total_size, is_remote_upload=True)

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
                f"#RemoteUpload:\n\nUser {user_mention} (`{message.from_user.id}`) uploaded file to ClawBox using @{BOT_USERNAME} !!\n\n**Downloaded in:** `{TimeFormatter(milliseconds=round(down_end-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-start)*1000)}`\n**FileName:** `{file_details['Original_File_Name']}`\n**File Size:** `{human_size(file_details['File_size'])}`\n**Share URL:** https://www.clawbox.in/s/{file_details['FileID']}",
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
        shutil.rmtree(os.path.dirname(file_location), ignore_errors=True)
    except:
        pass
