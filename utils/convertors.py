# (c) Mr. Avishkar

from pytz import timezone
from datetime import datetime

tz = timezone("Asia/Kolkata")

def convert_timestamp_to_datetime(timestamp):
    normal_date = datetime.fromisoformat(timestamp).astimezone(tz=tz)
    formatted_date = normal_date.strftime("%B %d, %Y %I:%M:%S %p")
    return formatted_date
