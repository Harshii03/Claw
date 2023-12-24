# (c) Mr. Avishkar

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.types import Message

import config
from handlers.database import UsersDatabase
from helpers.clawbox import ClawBox
from handlers.check_user import handle_user_status

from pyromod.exceptions import ListenerTimeout

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = UsersDatabase(DB_URL, DB_NAME)

@Bot.on_message(filters.command("login"))
async def login(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id

    clawbox = ClawBox()

    init_msg = await message.reply("Your Email?", quote=True)

    try:
        email = await bot.listen(chat_id=chat_id, user_id=message.from_user.id, timeout=60)
    except ListenerTimeout:
        return await init_msg.edit("Timeout")

    temp = await init_msg.reply("Password?", quote=True)

    try:
        password = await bot.listen(chat_id=chat_id, user_id=message.from_user.id, timeout=60)
    except ListenerTimeout:
        await temp.delete(True)
        return await init_msg.edit("Timeout")
    
    response = await clawbox.login(email=email.text, password=password.text)

    if response:
        await temp.delete(True)
        await password.delete(True)

        account = await clawbox.get_account_details()
        db.login_clawbox(message.from_user.id, account, response['token']['refresh'])

        await init_msg.reply(f"Successfully logined as **{account['name']}**", quote=True)
    else:
        await password.reply(f"Invalid credentials ;(", quote=True)

@Bot.on_message(filters.command("logout"))
async def logout(bot: Bot, message: Message):
    await handle_user_status(bot, message)
    chat_id = message.from_user.id
    db.logout_clawbox(chat_id)
    await message.reply(f"Successfully logout..", quote=True)