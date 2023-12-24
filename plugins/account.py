# (c) Mr. Avishkar

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from utils.file_size import human_size
from handlers.check_user import handle_user_status
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
AUTH_USERS = config.AUTH_USERS

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("account"))
async def account(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id
    refresh_token = db.get_refresh_token(chat_id)

    if refresh_token:
        clawbox = ClawBox(refresh_token)

        _temp = await message.reply("Fetching account details...", quote=True)

        account = await clawbox.get_account_details()

        stats = await clawbox.get_account_stats()
        balance = await clawbox.get_balance()

        captn = (
            f"<b>Account Details:</b>\n\n"
            f"<b>Name:</b> <code>{account['name']}</code>\n"
            f"<b>Email:</b> <code>{account['email']}</code>\n\n"
            f"<b>📦 Storage Details:</b>\n\n"
            f"<b>Total:</b> <code>{human_size(stats['allocatedstorage'])}</code>\n"
            f"<b>Used:</b> <code>{human_size(stats['totalstorage'])}</code>\n"
            f"<b>Free:</b> <code>{human_size(stats['leftstorage'])}</code>\n\n"
            f"<b>🦾 WebMaster Details:</b>\n\n"
            f"<b>Total Views:</b> <code>{balance['totalviews']}</code>\n"
            f"<b>Total Referrals:</b> <code>{balance['totalreferrals']}</code>\n"
            f"<b>Total Files:</b> <code>{stats['totalfileupload']}</code>\n\n"
            f"<b>💰 Webmaster Income:</b>\n\n"
            f"<b>Total Earned Income:</b> <code>${balance['totalearnings']}</code>\n"
            f"<b>Total Withdrawal Amount Left:</b> <code>${balance['earnings']}</code>\n\n"
            f"<b>⚠️ Note:</b> <code>This info seems not accurate? Please check clawbox.in (Desktop Mode)</code>"
        )

        btn = None

        if balance['earnings']:
            btn = [[
                InlineKeyboardButton("Request Payout 💰", callback_data="requestPay")
            ]]

        await _temp.edit(
            captn,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btn) if btn else None,
        )
    else:
        await message.reply(
            f"Kindly login to the bot to use it.\n\n**Tip:** Use /login to login into the bot.",
            parse_mode=ParseMode.MARKDOWN,
            quote=True,
        )
