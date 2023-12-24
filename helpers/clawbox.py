import json
import logging
import random
import re
import string
import time
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests_toolbelt import MultipartEncoder


class ClawBox:
    def __init__(self, refresh_token=None) -> None:
        self.ua = UserAgent()
        self.API_VERSION = "v1"
        self.user_agent = self.ua.random
        self.refresh_token = refresh_token
        self.CLAWBOX_API_DOMAIN = "api-prod.clawbox.in"
        self.UPLOAD_AUTH_TOKEN = None
        self.session = httpx.AsyncClient()

    async def listFiles(self):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        return (
            await self.session.get(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/user/getfiles/fulllist/",
                headers=HEADERS,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

    async def copyFile(self, fileID):
        HEADERS = {
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        res = await self.session.post(
            f"https://{self.CLAWBOX_API_DOMAIN}/api/file/copy/",
            data=json.dumps({"file_token": [fileID]}),
            headers=HEADERS,
            timeout=httpx.Timeout(180.0),
        )

        if res.is_success or res.status_code == 400:
            return res.status_code, res.json()
        return res.status_code, None

    async def getAuthToken(self):
        url = f"https://{self.CLAWBOX_API_DOMAIN}/api/user/token/refresh/"

        payload = {'refresh': self.refresh_token}

        headers = {
            'Accept': 'application/json'
        }

        response = await self.session.post(url, headers=headers, data=payload)
        return response.json()['access']

    async def login(self, email, password):
        url = f"https://{self.CLAWBOX_API_DOMAIN}/api/user/login/"

        payload = json.dumps({
            "email": email,
            "password": password
        })

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        response = await self.session.post(url, headers=headers, data=payload)

        if response.is_success:
            resp = response.json()
            self.refresh_token = resp['token']['refresh']
            return resp
        return None

    async def init_upload(self, FILE_NAME, FILE_SIZE, MIME_TYPE, is_remote_upload=False):
        HEADERS = {
            "Accept": "application/json, */*",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Req-Type": "start",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        if is_remote_upload:
            HEADERS['x-remote-upload'] = 'True'

        DATA = json.dumps({
            "file_name": FILE_NAME,
            "file_type": MIME_TYPE,
            "file_size": FILE_SIZE
        })

        self.UPLOAD_START_TIME = int(time.time())
        self.FILES_MD5 = []
        self.PART_SEQ = 1

        response = (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/upload/multipart/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

        self.FILE_UPLOAD_ID = response["id"]

        if is_remote_upload:
            return True, response["file_id"]
        return True

    async def upload_bytes(self, BINARY_DATA):
        files = {"file": BINARY_DATA}
        payload = {'file_id': self.FILE_UPLOAD_ID, 'part_number': self.PART_SEQ}

        if not self.UPLOAD_AUTH_TOKEN:
            self.UPLOAD_AUTH_TOKEN = await self.getAuthToken()

        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.UPLOAD_AUTH_TOKEN}",
            "X-Req-Type": "upload",
            "X-Requested-Through": "telegram-bot",
        }

        try:
            res = await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/upload/multipart/",
                timeout=httpx.Timeout(180.0),
                headers=HEADERS,
                data=payload,
                files=files,
            )
        except:
            self.UPLOAD_AUTH_TOKEN = await self.getAuthToken()

            HEADERS["Authorization"] = f"Bearer {self.UPLOAD_AUTH_TOKEN}"

            res = await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/upload/multipart/",
                timeout=httpx.Timeout(180.0),
                headers=HEADERS,
                data=payload,
                files=files,
            )

        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401
        if res.status_code == 401:
            self.UPLOAD_AUTH_TOKEN = await self.getAuthToken()

            HEADERS["Authorization"] = f"Bearer {self.UPLOAD_AUTH_TOKEN}"

            res = await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/upload/multipart/",
                timeout=httpx.Timeout(180.0),
                headers=HEADERS,
                data=payload,
                files=files,
            )

        self.PART_SEQ += 1

        return True

    async def finalize_upload(self, is_remote_upload=False):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Req-Type": "finish",
            "X-Requested-Through": "telegram-bot",
        }

        if is_remote_upload:
            HEADERS['x-remote-upload'] = 'True'

        data = {'file_id': self.FILE_UPLOAD_ID}

        response = await self.session.post(
            f"https://{self.CLAWBOX_API_DOMAIN}/api/file/upload/multipart/",
            headers=HEADERS,
            data=data,
            timeout=httpx.Timeout(180.0),
        )
        return response.json()
    
    async def updateDetails(self, fileID: str, newFileSize: int, is_remote_upload: bool = False):
        HEADERS = {
            "Accept": "application/json, */*",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Req-Type": "start",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        if is_remote_upload:
            HEADERS['x-remote-upload'] = 'True'

        DATA = json.dumps({
            "file_token": fileID,
            "file_size": newFileSize
        })

        res = (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/.updateDetails/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()
        return res

    async def copy(self, fileID=None):
        details = await self.fileDetails(fileID)

        if details.get("error"):
            return None, "No file found might me file deleted or the link is invalid."

        status_code, newDetails = await self.copyFile(
            fileID
        )
        if status_code == 400:
            return None, "You already own this file."

        return await self.fileDetails(newDetails['id']), f"https://www.clawbox.in/s/{newDetails['id']}"

    async def get_account_details(self):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Requested-Through": "telegram-bot",
        }
        res = (
            await self.session.get(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/user/profile/",
                headers=HEADERS,
                timeout=httpx.Timeout(180.0),
            )
        ).json()
        return res

    async def get_account_stats(self):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Requested-Through": "telegram-bot",
        }
        res = (
            await self.session.get(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/user/stats/",
                headers=HEADERS,
                timeout=httpx.Timeout(180.0),
            )
        ).json()
        return res

    async def get_balance(self):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "X-Requested-Through": "telegram-bot",
        }
        res = (
            await self.session.get(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/user/earnings/",
                headers=HEADERS,
                timeout=httpx.Timeout(180.0),
            )
        ).json()
        return res

    async def fileDetails(self, fileID, public=False):
        if not self.refresh_token and public:
            HEADERS = {
                "Accept": "application/json",
                "X-Requested-Through": "telegram-bot",
            }
            DATA = {'fileID': fileID}

            return (
                await self.session.post(
                    f"https://{self.CLAWBOX_API_DOMAIN}/api/file/details/",
                    headers=HEADERS,
                    data=DATA,
                    timeout=httpx.Timeout(180.0),
                )
            ).json()
        else:
            HEADERS = {
                "Accept": "application/json",
                "Authorization": f"Bearer {await self.getAuthToken()}",
                "x-file-token": fileID,
                "X-Requested-Through": "telegram-bot",
            }

            return (
                await self.session.get(
                    f"https://{self.CLAWBOX_API_DOMAIN}/api/file/details/",
                    headers=HEADERS,
                    timeout=httpx.Timeout(180.0),
                )
            ).json()
        
    async def favourite(self, fileID: str):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }
        DATA = json.dumps({
            "file_token": [
                fileID
            ]
        })
        return (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/favourite/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

    async def unfavourite(self, fileID: str):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }
        DATA = json.dumps({
            "file_token": [
                fileID
            ]
        })
        return (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/unfavourite/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

    async def delete(self, fileID: str):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }
        DATA = json.dumps({
            "file_token": [
                fileID
            ]
        })
        return (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/file/delete/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

    async def request_payout(self, payDetails: dict, amount: int):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        DATA = json.dumps({
            "pay_details": json.dumps(payDetails),
            "reqearning": amount
        })

        res = (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/payments/requestpayout/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

        return res

    async def request_status(self, req_id: str):
        HEADERS = {
            "Accept": "application/json",
            "Authorization": f"Bearer {await self.getAuthToken()}",
            "Content-Type": "application/json",
            "X-Requested-Through": "telegram-bot",
        }

        DATA = json.dumps({
            "req_id": req_id
        })

        res = (
            await self.session.post(
                f"https://{self.CLAWBOX_API_DOMAIN}/api/payments/requestpayoutstatus/",
                headers=HEADERS,
                data=DATA,
                timeout=httpx.Timeout(180.0),
            )
        ).json()

        return res