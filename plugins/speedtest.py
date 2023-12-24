# (c) Mr. Avishkar

import logging

from pyrogram import Client as Bot
from pyrogram import filters
from pyrogram.types import Message
from speedtest import Speedtest

import config
from handlers.database import UsersDatabase
from handlers.check_user import handle_user_status

DB_URL = config.DB_URL
DB_NAME = config.DB_NAME
AUTH_USERS = config.AUTH_USERS

db = UsersDatabase(DB_URL, DB_NAME)

def speed_convert(size):
    """Hi human, you can't read bytes?"""
    power = 1000
    zero = 0
    units = {0: "Bytes", 1: "KiB", 2: "MiB", 3: "GiB", 4: "TiB"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"


@Bot.on_message(filters.command("speedtest"))
async def speedtest(_: Bot, message: Message):
    await handle_user_status(_, message)
    speed = await message.reply("<i>Initializing Speedtest...</i>", quote=True)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = result["share"]
    string_speed = f"""
➲ <b><i>SPEEDTEST INFO</i></b>
┠ <b>Download:</b>  <code>{speed_convert(result['download'])}/s</code>
┠ <b>Upload:</b> <code>{speed_convert(result['upload'])}/s</code>
┠ <b>Ping:</b> <code>{result['ping']} ms</code>
┠ <b>Time:</b> <code>{result['timestamp']}</code>
┠ <b>Data Sent:</b> <code>{speed_convert(int(result['bytes_sent']))}</code>
┖ <b>Data Received:</b> <code>{speed_convert(int(result['bytes_received']))}</code>

➲ <b><i>SPEEDTEST SERVER</i></b>
┠ <b>Name:</b> <code>{result['server']['name']}</code>
┠ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
┠ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
┠ <b>Latency:</b> <code>{result['server']['latency']}</code>
┠ <b>Latitude:</b> <code>{result['server']['lat']}</code>
┖ <b>Longitude:</b> <code>{result['server']['lon']}</code>

➲ <b><i>CLIENT DETAILS</i></b>
┠ <b>IP Address:</b> <code>{result['client']['ip']}</code>
┠ <b>Latitude:</b> <code>{result['client']['lat']}</code>
┠ <b>Longitude:</b> <code>{result['client']['lon']}</code>
┠ <b>Country:</b> <code>{result['client']['country']}</code>
┠ <b>ISP:</b> <code>{result['client']['isp']}</code>
┖ <b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
"""
    try:
        await message.reply_photo(path, quote=True, caption=string_speed)
        try:
            await speed.delete(True)
        except:
            pass
    except Exception as e:
        logging.error(str(e))
        await speed.edit(string_speed)
