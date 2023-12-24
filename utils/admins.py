# (c) Mr. Avishkar

from pyrogram import Client
from pyrogram.types import Message

async def tag_admins(app: Client, message: Message):
    text = ""
    admin_data = [
        i async for i in app.get_chat_members(chat_id=message.chat.id)
    ]
    for admin in admin_data:
        if admin.user.is_bot or admin.user.is_deleted:
            continue
        text += f"[\u2063](tg://user?id={admin.user.id})"

    return text
