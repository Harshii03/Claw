import time

from pyrogram.enums import ChatAction

import config
from helpers.progress import progress_for_pyrogram

LOG_CHANNEL = config.LOG_CHANNEL


async def download_file(bot, message, status_msg, faster_download=False):
    suid = str(time.time()).replace(".", "")
    DOWNLOADS_FOLDER = f"./DOWNLOADS/{suid}/"
    start_time = time.time()
    if faster_download and bot.userbot is not None:
        await status_msg.edit("**🚀 Using Turbo engine for downloading file...**")
        _temp = await message.forward(LOG_CHANNEL)
        __temp = await bot.userbot.get_messages(_temp.chat.id, _temp.id)
        file_path = await bot.userbot.download_media(
            __temp,
            file_name=DOWNLOADS_FOLDER,
            progress=progress_for_pyrogram,
            progress_args=(
                "📥Downloading...",
                status_msg,
                start_time,
                bot,
                ChatAction.PLAYING,
            ),
        )
        try:
            await _temp.delete(True)
        except:
            pass
    else:
        await status_msg.edit("**🥹 Using Regular engine for downloading file...**")
        file_path = await message.download(
            DOWNLOADS_FOLDER,
            progress=progress_for_pyrogram,
            progress_args=(
                "📥Downloading...",
                status_msg,
                start_time,
                bot,
                ChatAction.PLAYING,
            ),
        )
    await status_msg.edit("File Downloaded Successfully...")
    return file_path
