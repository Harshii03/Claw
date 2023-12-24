import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

COOKIES = {
    "csrfToken": "x0h2WkCSJZZ_ncegDtpABKzt",
    "browserid": "Bx3OwxDFKx7eOi8np2AQo2HhlYs5Ww9S8GDf6Bg0q8MTw7cl_3hv7LEcgzk=",
    "lang": "en",
    "TSID": "pdZVCjBvomsN0LnvT407VJiaJZlfHlVy",
    "__bid_n": "187fc5b9ec480cfe574207",
    "ndus": "Y-ZNVKxteHuixZLS-xPAQRmqh5zukWbTHVjen34w",
    "__stripe_mid": "895ddb1a-fe7d-43fa-a124-406268fe0d0c36e2ae",
    "ndut_fmt": "FF870BBFA15F9038B3A39F5DDDF1188864768A8E63DC6AEC54785FCD371BB182",
}

class TeraBox:
    def __init__(self, cookies=COOKIES, isLogined=True) -> None:
        self.ua = UserAgent()
        self.APP_ID = 250528
        self.user_agent = self.ua.random
        self.JS_TOKEN_PATTERN = re.compile(
            r"decodeURIComponent\(\`([^)]*)\`\)", re.IGNORECASE
        )
        self.cookies = cookies
        self.isLogined = isLogined
        self.TERABOX_API_DOMAIN = "www.4funbox.com"
        self.session = httpx.AsyncClient()

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": f"d.4funbox.com",
            "User-Agent": self.user_agent,
            "Upgrade-Insecure-Requests": "1",
        }

    async def init(self, shareURL=None):
        self.shareURL = shareURL
        self.JS_TOKEN = await self.getJSToken(shareURL)

    async def getJSToken(self, shareURL=None):
        HEADERS = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Host": f"{self.TERABOX_API_DOMAIN}",
            "Origin": f"https://{self.TERABOX_API_DOMAIN}",
            "Referer": f"https://{self.TERABOX_API_DOMAIN}/"
            if not shareURL
            else f"https://{self.TERABOX_API_DOMAIN}/sharing/link?surl={shareURL}",
            "User-Agent": self.user_agent,
        }
        if self.isLogined:
            html = (
                await self.session.get(
                    f"https://{self.TERABOX_API_DOMAIN}/main",
                    headers=HEADERS,
                    cookies=self.cookies,
                    timeout=httpx.Timeout(180.0),
                )
            ).text
        else:
            html = (
                await self.session.get(
                    f"https://{self.TERABOX_API_DOMAIN}",
                    headers=HEADERS,
                    timeout=httpx.Timeout(180.0),
                )
            ).text
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", string=self.JS_TOKEN_PATTERN)
        if script:
            match = self.JS_TOKEN_PATTERN.search(script.text)
            if match:
                token = unquote(match.group(1))
                token_pattern = re.compile(r"fn\(\"([^)]*)\"\)", re.IGNORECASE)
                return re.findall(token_pattern, token)[0]
        return None

    def find_between(self, string, start, end):
        start_index = string.find(start) + len(start)
        end_index = string.find(end, start_index)
        if start_index != -1 and end_index != -1:
            return string[start_index:end_index]
        else:
            return ""
        
    def is_valid_url(self, url):
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https", "ftp"):
                return False
            if not parsed_url.netloc:
                return False
            return True
        except ValueError:
            return False

    def is_terabox_url(self, url):
        patterns = [
            r"ww\.mirrobox\.com",
            r"www\.nephobox\.com",
            r"freeterabox\.com",
            r"www\.freeterabox\.com",
            r"1024tera\.com",
            r"4funbox\.co",
            r"www\.4funbox\.com",
            r"mirrobox\.com",
            r"nephobox\.com",
            r"terabox\.app",
            r"terabox\.com",
            r"www\.terabox\.ap",
            r"terabox\.fun",
            r"www\.terabox\.com",
            r"www\.1024tera\.co",
            r"www\.momerybox\.com",
            r"teraboxapp\.com",
            r"momerybox\.com",
            r"tibibox\.com",
            r"www\.tibibox\.com",
            r"www\.teraboxapp\.com",
        ]

        if not self.is_valid_url(url):
            return False

        for pattern in patterns:
            if re.search(pattern, url):
                return True

        return False

    async def get_download_url(self, url):
        resp = await self.session.get(
            url, follow_redirects=True, timeout=httpx.Timeout(180.0)
        )
        surl = parse_qs(urlparse(str(resp.url)).query).get("surl", [""])[0]

        HEADERS = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": f"{self.TERABOX_API_DOMAIN}",
            "Origin": f"https://{self.TERABOX_API_DOMAIN}",
            "Referer": f"https://{self.TERABOX_API_DOMAIN}/sharing/link?surl={surl}",
            "User-Agent": self.user_agent,
            "X-Requested-With": "XMLHttpRequest",
        }

        LOG_ID = self.find_between(resp.text, "dp-logid=", "&")

        PARAMS = {
            "app_id": self.APP_ID,
            "web": "1",
            "channel": "dubox",
            "clienttype": "0",
            "jsToken": self.JS_TOKEN,
            "page": "1",
            "num": "20",
            "order": "time",
            "desc": "1",
            "site_referer": str(resp.url),
            "shorturl": surl,
            "dplogid": LOG_ID,
            "root": "1",
        }

        return (
            await self.session.get(
                f"https://{self.TERABOX_API_DOMAIN}/share/list",
                params=PARAMS,
                headers=HEADERS,
                cookies=self.cookies,
                timeout=httpx.Timeout(180.0),
            )
        ).json()