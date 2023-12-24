import math
import time

from psutil import cpu_percent, disk_usage, net_io_counters, virtual_memory

async def progress_for_pyrogram(
    current, total, ud_type, message, start, bot, chatAction=None
):
    now = time.time()
    diff = now - start
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "**[{0}{1}] » ({2}%)**\n".format(
            "".join(["▰" for i in range(math.floor(percentage / 10))]),
            "".join(["▱" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2),
        )

        tmp = (
            progress
            + "**🔄 Process »** `{0}` of `{1}`\n**⚡️ Speed »** `{2}/s`\n**⌛️ ETA »** `{3}` | **Active »** `{4}`\n\n**🖥️ CPU:** `{5}%` | **💽 RAM:** `{6}%`\n**📭 Free:** `{7}` | **⏰ Uptime:** `{8}`\n**🔻 DL:** `{9}` | **🔺 UL:** `{10}`".format(
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),
                estimated_total_time if estimated_total_time != "" else "0 s",
                elapsed_time if elapsed_time != "" else "0 s",
                cpu_percent(),
                virtual_memory().percent,
                humanbytes(disk_usage(".").free),
                TimeFormatter(round(time.time() - bot.uptime) * 1000),
                humanbytes(net_io_counters().bytes_recv),
                humanbytes(net_io_counters().bytes_sent),
            )
        )
        if chatAction:
            try:
                await message.reply_chat_action(chatAction)
            except:
                pass
        try:
            await message.edit(text="{}\n\n{}".format(ud_type, tmp))
        except:
            pass


def humanbytes(size, power=2**10):
    if not size:
        return ""
    n = 0
    Dic_powerN = {0: " ", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        n += 1
    return (str(round(size, 2)) + " " + Dic_powerN[n] + "B").replace('  ', ' ')


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d ") if days else "")
        + ((str(hours) + "h ") if hours else "")
        + ((str(minutes) + "m ") if minutes else "")
        + ((str(seconds) + "s ") if seconds else "")
        + ((str(milliseconds) + "ms ") if milliseconds else "")
    )
    return tmp.strip()
