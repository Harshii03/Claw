# (c) Mr. Avishkar


import hashlib
import json
import os
import shutil
import time

import aiofiles
import ffmpeg
import httpx
import magic
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

from psutil import (
    boot_time,
    cpu_count,
    cpu_percent,
    disk_usage,
    net_io_counters,
    swap_memory,
    virtual_memory,
)
from pyrogram import Client as Bot
from pyrogram.errors import MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction, ParseMode

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from helpers.progress import TimeFormatter, humanbytes, progress_for_pyrogram
from utils.Nekmo_ffmpeg import get_thumbnail
from utils.convertors import convert_timestamp_to_datetime
from utils.formatters import get_readable_file_size, get_readable_time

AUTH_USERS = config.AUTH_USERS
DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = UsersDatabase(DB_URL, DB_NAME)

PAYOUT_OPTIONS = {
    "upi": "UPI",
    "gpay": "GPay",
    "paytm": "Paytm",
    "paypal": "PayPal",
    "phonepe": "PhonePe",
}


async def getFileIDfromMD5(clawbox: ClawBox, md5: str):
    files = await clawbox.listFiles()
    cacheDB = json.loads(open("fileID.db", "w+").read() or "{}")
    if md5 not in cacheDB:
        for file in files:
            proposedMD5 = hashlib.md5(file['FileID'].encode()).hexdigest()
            if proposedMD5 == md5:
                cacheDB[md5] = file['FileID']
                json.dump(cacheDB, open("fileID.db", "w+"))
                return file['FileID']
            else:
                cacheDB[proposedMD5] = file['FileID']
    else:
        return cacheDB[md5]

    return None

async def listFiles(cb: CallbackQuery, page: int | None = None):
    _, _page = cb.data.split("_", 1)
    page = int(_page) if page is None else page
    refresh_token = db.get_refresh_token(cb.from_user.id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)
    
        files = await clawbox.listFiles()

        if (not isinstance(files, list)) and files.get("error"):
            return await cb.message.edit(files.get("error"))

        btns = []

        for file in files[(6*page):(6*page)+6]:
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
                    f"[{page+1}/{int(len(files)/6)+1 if len(files) > 6 else 1}]",
                    callback_data="noop"
                )
            ]
        )
        nav_btn = []

        if page != 0:
            nav_btn.append(
                InlineKeyboardButton(
                    f"👈 Back",
                    callback_data=f"list_{page-1}",
                )
            )
        if len(files) > 6 and page < int(len(files)/6):
            nav_btn.append(
                InlineKeyboardButton(
                    f"Next 👉",
                    callback_data=f"list_{page+1}",
                )
            )
        btns.append(nav_btn)

        try:
            await cb.message.edit_reply_markup(InlineKeyboardMarkup(btns))
        except MessageNotModified:
            pass

        try:
            await cb.message.edit_caption(f"Found **{len(files)} files** in your ClawBox account.", reply_markup=InlineKeyboardMarkup(btns))
        except MessageNotModified:
            pass

@Bot.on_callback_query()
async def callback_handlers(bot: Bot, cb: CallbackQuery):
    user_id = cb.from_user.id
    bot_details = await bot.get_me()

    if cb.data == "notification":
        notif = db.get_notif(cb.from_user.id)
        if notif is True:
            db.set_notif(user_id, notif=False)
        else:
            db.set_notif(user_id, notif=True)
        await cb.message.edit(
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
        )
        await cb.answer(f"Successfully setted notifications to {db.get_notif(user_id)}")
    elif cb.data == "refreshStats":
        IS_ADMIN = False
        if cb.from_user.id in AUTH_USERS:
            IS_ADMIN = True

        try:
            total, used, free, disk = disk_usage(".")
            swap = swap_memory()
            memory = virtual_memory()

            stats = (
                f"<b>Bot Uptime:</b> `{get_readable_time(round(time.time() - bot.uptime) * 1000)}`\n"
                f"<b>OS Uptime:</b> `{get_readable_time(round(time.time() - boot_time()) * 1000)}`\n\n"
                f"<b>Total Disk Space:</b> `{get_readable_file_size(total)}`\n"
                f"<b>Used:</b> `{get_readable_file_size(used)}` | <b>Free:</b> `{get_readable_file_size(free)}`\n\n"
                f"<b>Upload:</b> `{get_readable_file_size(net_io_counters().bytes_sent)}`\n"
                f"<b>Download:</b> `{get_readable_file_size(net_io_counters().bytes_recv)}`\n\n"
                f"<b>CPU:</b> `{cpu_percent(interval=0.5)}%`\n"
                f"<b>RAM:</b> `{memory.percent}%`\n"
                f"<b>DISK:</b> `{disk}%`\n\n"
                f"<b>Physical Cores:</b> `{cpu_count(logical=False)}`\n"
                f"<b>Total Cores:</b> `{cpu_count(logical=True)}`\n\n"
                f"<b>SWAP:</b> `{get_readable_file_size(swap.total)}` | <b>Used:</b> `{swap.percent}%`\n"
                f"<b>Memory Total:</b> `{get_readable_file_size(memory.total)}`\n"
                f"<b>Memory Free:</b> `{get_readable_file_size(memory.available)}`\n"
                f"<b>Memory Used:</b> `{get_readable_file_size(memory.used)}`\n\n"
            )

            if IS_ADMIN:
                stats += f"**Total Users in UsersDatabase 📂:** `{db.total_users_count()}`\n\n**Total Users with Notification Enabled 🔔 :** `{db.total_notif_users_count()}`"

            await cb.message.edit(
                text=stats,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                f"Refresh 🔃",
                                callback_data="refreshStats",
                            )
                        ],
                        [InlineKeyboardButton("❎", callback_data="closeMeh")],
                    ]
                ),
            )
        except MessageNotModified:
            await cb.answer(f"Nothing to update ;) i.e. No new users or activity 😥")

    elif cb.data == "noop":
        return await cb.answer()

    elif cb.data.startswith("switchPM_"):
        _, command = cb.data.split("_", 1)
        username = (await bot.get_me()).username
        return await cb.answer(url=f"https://t.me/{username}?start=command_{command}")
    
    elif cb.data.startswith("list_"):
        await listFiles(cb)

    elif cb.data.startswith("dl_"):
        _, md5 = cb.data.split("_")
        refresh_token = db.get_refresh_token(cb.from_user.id)

        if refresh_token:
            clawbox = ClawBox(refresh_token)
            fileID = await getFileIDfromMD5(clawbox, md5)
            
            if fileID:
                file = await clawbox.fileDetails(fileID)
                await cb.answer("File download initiated successfully 😴", show_alert=True)

                config.ONGOING_DOWNLOAD_PROCESSES[cb.from_user.id] = config.ONGOING_DOWNLOAD_PROCESSES.get(cb.from_user.id, 0) + 1

                status_msg = await cb.message.reply(
                    f"Getting file details 📦...", parse_mode=ParseMode.MARKDOWN, quote=True
                )
                dl_url = f"https://{clawbox.CLAWBOX_API_DOMAIN}/api/file/get/d/{file['FileID']}/"

                await status_msg.edit(
                    f"Starting download from ClawBox 📦...", parse_mode=ParseMode.MARKDOWN
                )

                down_start = time.time()
                username = (await bot.get_me()).username

                suid = str(time.time()).replace(".", "")
                DOWNLOADS_FOLDER = f"./DOWNLOADS/{suid}/"
                os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

                file_location = (
                    f"{DOWNLOADS_FOLDER}[Downloaded By @{username}]_{file['Original_File_Name']}"
                )

                HEADERS = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "en-US,en;q=0.9"
                }

                async with aiofiles.open(file_location, mode="wb") as _file:
                    async with clawbox.session.stream(
                        "GET",
                        dl_url,
                        headers=HEADERS,
                        timeout=httpx.Timeout(180.0),
                        follow_redirects=True,
                    ) as response:
                        total = int(file["File_size"])
                        async for chunk in response.aiter_bytes():
                            await _file.write(chunk)
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

                CAPTION = f"**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n\n**📁 File Name:** `{file['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(file['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(file['Modified_At'])}`\n**🔗 URL:** https://www.clawbox.in/s/{file['FileID']}"
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

                    if int(file["File_size"]) >= 2097152000:
                        __downloaded = await bot.userbot.send_video(
                            config.LOG_CHANNEL,
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
                            chat_id=cb.message.chat.id,
                            from_chat_id=__downloaded.chat.id,
                            message_id=__downloaded.id,
                            reply_to_message_id=cb.message.id,
                            caption=CAPTION,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton(
                                            f"🤖 Uploaded By @{bot_details.username}",
                                            url=f"https://t.me/{bot_details.username}",
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
                        _downloaded = await cb.message.reply_video(
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
                                            f"🤖 Uploaded By @{bot_details.username}",
                                            url=f"https://t.me/{bot_details.username}",
                                        )
                                    ]
                                ]
                            ),
                            quote=True,
                        )
                else:
                    if int(file["File_size"]) >= 2097152000 and bot.userbot:
                        __downloaded = await bot.userbot.send_document(
                            config.LOG_CHANNEL,
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
                            chat_id=cb.message.chat.id,
                            from_chat_id=__downloaded.chat.id,
                            message_id=__downloaded.id,
                            reply_to_message_id=cb.message.id,
                            caption=CAPTION,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton(
                                            f"🤖 Uploaded By @{bot_details.username}",
                                            url=f"https://t.me/{bot_details.username}",
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
                        _downloaded = await cb.message.reply_document(
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
                                            f"🤖 Uploaded By @{bot_details.username}",
                                            url=f"https://t.me/{bot_details.username}",
                                        )
                                    ]
                                ]
                            ),
                            quote=True,
                        )

                try:
                    await _downloaded.edit_caption(
                        f"**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n\n**📁 File Name:** `{file['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(file['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(file['Modified_At'])}`\n**🔗 URL:** https://www.clawbox.in/s/{file['FileID']}",
                        reply_markup=_downloaded.reply_markup,
                    )
                except MessageNotModified:
                    pass

                config.ONGOING_DOWNLOAD_PROCESSES[cb.message.chat.id] = config.ONGOING_DOWNLOAD_PROCESSES.get(cb.message.chat.id) - 1

                if config.LOG_CHANNEL:
                    _forwared = await _downloaded.forward(config.LOG_CHANNEL)
                    user_mention = cb.message.from_user.mention(
                        f"{cb.message.from_user.first_name}{' '+cb.message.from_user.last_name if cb.message.from_user.last_name else ''}",
                        style=ParseMode.MARKDOWN,
                    )
                    await _forwared.reply(
                        f"#NewFileDownloaded:\n\nUser {user_mention} (`{cb.message.from_user.id}`) downloaded a file from ClawBox using @{bot_details.username} !!\n\n**Downloaded in:** `{TimeFormatter(milliseconds=round(upload_start-down_start)*1000)}`\n**Uploaded in:** `{TimeFormatter(milliseconds=round(time.time()-upload_start)*1000)}`\n**📁 File Name:** `{file['Original_File_Name']}`\n**🗳️ File Size:** `{humanbytes(int(file['File_size']))}`\n**⏰ Uploaded On:** `{convert_timestamp_to_datetime(file['Modified_At'])}`\n**🔗 URL:** https://www.clawbox.in/s/{file['FileID']}",
                        parse_mode=ParseMode.MARKDOWN,
                        quote=True,
                    )

                try:
                    await status_msg.delete(True)
                    shutil.rmtree(os.path.dirname(file_location), ignore_errors=True)
                except:
                    pass
            else:
                return await cb.answer("File not found.", show_alert=True)
        else:
            await cb.answer("Kindly, login into the bot using /login", show_alert=True)

    elif cb.data.startswith("d_"):
        _, md5 = cb.data.split("_")
        refresh_token = db.get_refresh_token(cb.from_user.id)

        if refresh_token:
            clawbox = ClawBox(refresh_token)
            fileID = await getFileIDfromMD5(clawbox, md5)
            
            if fileID:
                file = await clawbox.fileDetails(fileID)
                await clawbox.delete(fileID=file["FileID"])
                await cb.answer("File moved to Recycle Bin 🗑️", show_alert=True)
                return await listFiles(cb, page=0)
            else:
                return await cb.answer("File not found.", show_alert=True)
        else:
            await cb.answer("Kindly, login into the bot using /login", show_alert=True)

    elif cb.data.startswith("f_"):
        _, md5 = cb.data.split("_")
        refresh_token = db.get_refresh_token(cb.from_user.id)

        if refresh_token:
            clawbox = ClawBox(refresh_token)
            fileID = await getFileIDfromMD5(clawbox, md5)

            if fileID:
                file = await clawbox.fileDetails(fileID)

                if file['Favourite'] is True:
                    await clawbox.unfavourite(fileID=file["FileID"])
                    await cb.answer("File successfully unfavourited.", show_alert=True)
                else:
                    await clawbox.favourite(fileID=file["FileID"])
                    await cb.answer("File successfully favourited.", show_alert=True)

                file = await clawbox.fileDetails(fileID)
                old_markup = cb.message.reply_markup.inline_keyboard

                for i, row in enumerate(old_markup):
                    for btn in row:
                        if btn.callback_data == cb.data:
                            old_markup[i] = [
                                InlineKeyboardButton(
                                    file['Original_File_Name'],
                                    callback_data=f"v_{md5}"
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
                
                try:
                    await cb.message.edit_reply_markup(InlineKeyboardMarkup(old_markup))
                except MessageNotModified:
                    pass
            else:
                return await cb.answer("File not found.", show_alert=True)
        else:
            await cb.answer("Kindly, login into the bot using /login", show_alert=True)

    elif cb.data.startswith("fd_"):
        _, md5 = cb.data.split("_")
        refresh_token = db.get_refresh_token(cb.from_user.id)

        if refresh_token:
            clawbox = ClawBox(refresh_token)
            fileID = await getFileIDfromMD5(clawbox, md5)

            if fileID:
                file = await clawbox.fileDetails(fileID)

                if file['Favourite'] is True:
                    await clawbox.unfavourite(fileID=file["FileID"])
                    await cb.answer("File successfully unfavourited.", show_alert=True)
                else:
                    await clawbox.favourite(fileID=file["FileID"])
                    await cb.answer("File successfully favourited.", show_alert=True)

                file = await clawbox.fileDetails(fileID)

                try:
                    await cb.message.edit(
                        f"**File Details:**\n\n**Name:** `{file['Original_File_Name']}`\n**Size:** `{humanbytes(int(file['File_size']))}`\n**Timestamp:** `{convert_timestamp_to_datetime(file['Modified_At'])}`\n**Type:** `{file['File_type']}`\n**Is Favourite:** `{'❤️ True' if (file['Favourite'] is True) else '🖤 False'}`",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        'Favourite ❤️' if (file['Favourite'] is False) else 'Unfavourite 💔',
                                        callback_data=f"fd_{md5}"
                                    ),
                                    InlineKeyboardButton(
                                        "⬇️ Download",
                                        callback_data=f"dl_{md5}"
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        'Delete 🗑️',
                                        callback_data=f"d_{md5}"
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        'Back 🔙',
                                        callback_data=f"list_0"
                                    )
                                ]
                            ]
                        )
                    )
                except MessageNotModified:
                    pass
            else:
                return await cb.answer("File not found.", show_alert=True)
        else:
            await cb.answer("Kindly, login into the bot using /login", show_alert=True)

    elif cb.data.startswith("v_"):
        _, md5 = cb.data.split("_")
        refresh_token = db.get_refresh_token(cb.from_user.id)

        if refresh_token:
            clawbox = ClawBox(refresh_token)
            fileID = await getFileIDfromMD5(clawbox, md5)
            
            if fileID:
                file = await clawbox.fileDetails(fileID)

                await cb.message.edit(
                    f"**File Details:**\n\n**Name:** `{file['Original_File_Name']}`\n**Size:** `{humanbytes(int(file['File_size']))}`\n**Timestamp:** `{convert_timestamp_to_datetime(file['Modified_At'])}`\n**Type:** `{file['File_type']}`\n**Is Favourite:** `{'❤️ True' if (file['Favourite'] is True) else '🖤 False'}`",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    'Favourite ❤️' if (file['Favourite'] is False) else 'Unfavourite 💔',
                                    callback_data=f"fd_{md5}"
                                ),
                                InlineKeyboardButton(
                                    "Share URL",
                                    url=f"https://clawbox.in/s/{file['FileID']}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    'Delete 🗑️',
                                    callback_data=f"d_{md5}"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    'Back 🔙',
                                    callback_data=f"list_0"
                                )
                            ]
                        ]
                    )
                )
            else:
                return await cb.answer("File not found.", show_alert=True)
        else:
            await cb.answer("Kindly, login into the bot using /login", show_alert=True)

    else:
        try:
            await cb.message.reply_to_message.delete(True)
            await cb.message.delete(True)
        except:
            pass
