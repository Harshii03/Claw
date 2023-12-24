# (c) Mr. Avishkar

import time

from aiofiles.os import path as aiopath
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
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from handlers.database import UsersDatabase
from utils.cmd_exec import cmd_exec
from utils.formatters import get_readable_file_size, get_readable_time
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
AUTH_USERS = config.AUTH_USERS

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("stats"))
async def stats(bot: Bot, message: Message):
    await handle_user_status(bot, message)

    IS_ADMIN = False

    if message.from_user.id in AUTH_USERS:
        IS_ADMIN = True

    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "No UPSTREAM_REPO"
    total, used, free, disk = disk_usage(".")
    swap = swap_memory()
    memory = virtual_memory()

    stats = (
        f"<b>Commit Date:</b> `{last_commit}`\n\n"
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

    await message.reply(
        stats,
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
        quote=True,
    )
