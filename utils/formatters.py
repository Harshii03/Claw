# (c) Mr. Avishkar

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def get_readable_time(milliseconds):
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


def get_readable_file_size(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: " ", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + "B"
