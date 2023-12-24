# (c) Mr. Avishkar

import base64
import os
import time

def download_data_uri(uri):
    head, data = uri.split(",", 1)
    file_ext = head.split(";")[0].split("/")[1]
    plain_data = base64.b64decode(data)

    suid = str(time.time()).replace(".", "")
    os.makedirs(f"./Login_QR/{suid}", exist_ok=True)

    with open(f"./Login_QR/{suid}/qr.{file_ext}", "wb") as f:
        f.write(plain_data)
    return f"./Login_QR/{suid}/qr.{file_ext}"
