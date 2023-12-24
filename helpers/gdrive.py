# (c) Mr. Avishkar

import functools
import inspect
import json
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
import textwrap
import aiofiles

import httpx
import requests
import six
import tqdm
import re
import warnings

from six.moves import urllib_parse

home = osp.expanduser("~")

class FileURLRetrievalError(Exception):
    pass

class GDrive:
    def get_url_from_gdrive_confirmation(self, contents):
        url = ""
        for line in contents.splitlines():
            m = re.search(r'href="(\/uc\?export=download[^"]+)', line)
            if m:
                url = "https://docs.google.com" + m.groups()[0]
                url = url.replace("&amp;", "&")
                break
            m = re.search('id="download-form" action="(.+?)"', line)
            if m:
                url = m.groups()[0]
                url = url.replace("&amp;", "&")
                break
            m = re.search('"downloadUrl":"([^"]+)', line)
            if m:
                url = m.groups()[0]
                url = url.replace("\\u003d", "=")
                url = url.replace("\\u0026", "&")
                break
            m = re.search('<p class="uc-error-subcaption">(.*)</p>', line)
            if m:
                error = m.groups()[0]
                raise FileURLRetrievalError(error)
        if not url:
            raise FileURLRetrievalError(
                "Cannot retrieve the public link of the file. "
                "You may need to change the permission to "
                "'Anyone with the link', or have had many accesses."
            )
        return url

    def parse_url(self, url, warning=True):
        parsed = urllib_parse.urlparse(url)
        query = urllib_parse.parse_qs(parsed.query)
        is_gdrive = parsed.hostname in ["drive.google.com", "docs.google.com"]
        is_download_link = parsed.path.endswith("/uc")

        if not is_gdrive:
            return is_gdrive, is_download_link

        file_id = None
        if "id" in query:
            file_ids = query["id"]
            if len(file_ids) == 1:
                file_id = file_ids[0]
        else:
            patterns = [
                r"^/file/d/(.*?)/(edit|view)$",
                r"^/file/u/[0-9]+/d/(.*?)/(edit|view)$",
                r"^/document/d/(.*?)/(edit|htmlview|view)$",
                r"^/document/u/[0-9]+/d/(.*?)/(edit|htmlview|view)$",
                r"^/presentation/d/(.*?)/(edit|htmlview|view)$",
                r"^/presentation/u/[0-9]+/d/(.*?)/(edit|htmlview|view)$",
                r"^/spreadsheets/d/(.*?)/(edit|htmlview|view)$",
                r"^/spreadsheets/u/[0-9]+/d/(.*?)/(edit|htmlview|view)$",
            ]
            for pattern in patterns:
                match = re.match(pattern, parsed.path)
                if match:
                    file_id = match.groups()[0]
                    break

        if warning and not is_download_link:
            warnings.warn(
                "You specified a Google Drive link that is not the correct link "
                "to download a file. You might want to try `--fuzzy` option "
                "or the following url: {url}".format(
                    url="https://drive.google.com/uc?id={}".format(file_id)
                )
            )

        return file_id, is_download_link

    def indent(self, text, prefix):
        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if line.strip() else line)

        return "".join(prefixed_lines())

    def _get_session(self, proxy, use_cookies, httpx_sess=True, return_cookies_file=False):
        if httpx_sess:
            sess = httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6)"}
            )
        else:
            sess = requests.session()

            sess.headers.update(
                {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6)"}
            )

        if proxy is not None:
            sess.proxies = {"http": proxy, "https": proxy}
            print("Using proxy:", proxy, file=sys.stderr)

        cookies_file = osp.join(home, ".cache/gdrive/cookies.json")
        if osp.exists(cookies_file) and use_cookies:
            with open(cookies_file) as f:
                cookies = json.load(f)
            for k, v in cookies:
                sess.cookies[k] = v

        if return_cookies_file:
            return sess, cookies_file
        else:
            return sess

    async def getDetails(
        self,
        url=None,
        proxy=None,
        use_cookies=True,
        verify=True,
        id=None,
        fuzzy=False,
        format=None,
    ):
        
        if not (id is None) ^ (url is None):
            raise ValueError("Either url or id has to be specified")
        if id is not None:
            url = "https://drive.google.com/uc?id={id}".format(id=id)

        url_origin = url

        gdrive_file_id, is_gdrive_download_link = self.parse_url(url, warning=not fuzzy)

        if fuzzy and gdrive_file_id:
            url = "https://drive.google.com/uc?id={id}".format(id=gdrive_file_id)
            url_origin = url
            is_gdrive_download_link = True

        __sess, cookies_file = self._get_session(
            proxy=proxy, use_cookies=use_cookies, httpx_sess=False, return_cookies_file=True
        )

        while True:
            res = __sess.get(url, stream=True, verify=verify)

            if url == url_origin and res.status_code == 500:
                url = "https://drive.google.com/open?id={id}".format(
                    id=gdrive_file_id
                )
                continue

            if res.headers["Content-Type"].startswith("text/html"):
                m = re.search("<title>(.+)</title>", res.text)
                if m and m.groups()[0].endswith(" - Google Docs"):
                    url = (
                        "https://docs.google.com/document/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="docx" if format is None else format,
                        )
                    )
                    continue
                elif m and m.groups()[0].endswith(" - Google Sheets"):
                    url = (
                        "https://docs.google.com/spreadsheets/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="xlsx" if format is None else format,
                        )
                    )
                    continue
                elif m and m.groups()[0].endswith(" - Google Slides"):
                    url = (
                        "https://docs.google.com/presentation/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="pptx" if format is None else format,
                        )
                    )
                    continue
            elif (
                "Content-Disposition" in res.headers
                and res.headers["Content-Disposition"].endswith("pptx")
                and format not in {None, "pptx"}
            ):
                url = (
                    "https://docs.google.com/presentation/d/{id}/export"
                    "?format={format}".format(
                        id=gdrive_file_id,
                        format="pptx" if format is None else format,
                    )
                )
                continue

            if use_cookies:
                if not osp.exists(osp.dirname(cookies_file)):
                    os.makedirs(osp.dirname(cookies_file))
                with open(cookies_file, "w") as f:
                    cookies = [
                        (k, v)
                        for k, v in __sess.cookies.items()
                        if not k.startswith("download_warning_")
                    ]
                    json.dump(cookies, f, indent=2)

            if "Content-Disposition" in res.headers:
                break
            if not (gdrive_file_id and is_gdrive_download_link):
                break
            try:
                url = self.get_url_from_gdrive_confirmation(res.text)
            except FileURLRetrievalError as e:
                message = (
                    "**Failed to retrieve file url:**\n\n```\n{}```\n\n"
                    "You may still be able to access the file from the browser:"
                    "\n\n\t{}\n\n"
                    "but I can't. Please check file and permissions."
                ).format(
                    self.indent("\n".join(textwrap.wrap(str(e))), prefix="\t"),
                    url_origin,
                )
                raise FileURLRetrievalError(message)

        if gdrive_file_id and is_gdrive_download_link:
            content_disposition = six.moves.urllib_parse.unquote(
                res.headers["Content-Disposition"]
            )
            m = re.search(r"filename\*=UTF-8''(.*)", content_disposition)
            filename_from_url = m.groups()[0]
            filename_from_url = filename_from_url.replace(osp.sep, "_")
        else:
            filename_from_url = osp.basename(url)

        total = res.headers.get("Content-Length")
        if total is not None:
            total = int(total)

        __sess.close()

        return {'filename': filename_from_url, 'size': total, 'mimetype': res.headers.get("content-type")}

    async def download(
        self,
        url=None,
        output=None,
        quiet=False,
        proxy=None,
        use_cookies=True,
        verify=True,
        id=None,
        fuzzy=False,
        resume=False,
        format=None,
        progress=None,
        progress_args=None,
    ):
        if not (id is None) ^ (url is None):
            raise ValueError("Either url or id has to be specified")
        if id is not None:
            url = "https://drive.google.com/uc?id={id}".format(id=id)

        url_origin = url

        sess, cookies_file = self._get_session(
            proxy=proxy, use_cookies=use_cookies, return_cookies_file=True
        )

        gdrive_file_id, is_gdrive_download_link = self.parse_url(url, warning=not fuzzy)

        if fuzzy and gdrive_file_id:
            url = "https://drive.google.com/uc?id={id}".format(id=gdrive_file_id)
            url_origin = url
            is_gdrive_download_link = True

        __sess, _ = self._get_session(
            proxy=proxy, use_cookies=use_cookies, httpx_sess=False, return_cookies_file=True
        )

        while True:
            res = __sess.get(url, stream=True, verify=verify)

            if url == url_origin and res.status_code == 500:
                url = "https://drive.google.com/open?id={id}".format(
                    id=gdrive_file_id
                )
                continue

            if res.headers["Content-Type"].startswith("text/html"):
                m = re.search("<title>(.+)</title>", res.text)
                if m and m.groups()[0].endswith(" - Google Docs"):
                    url = (
                        "https://docs.google.com/document/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="docx" if format is None else format,
                        )
                    )
                    continue
                elif m and m.groups()[0].endswith(" - Google Sheets"):
                    url = (
                        "https://docs.google.com/spreadsheets/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="xlsx" if format is None else format,
                        )
                    )
                    continue
                elif m and m.groups()[0].endswith(" - Google Slides"):
                    url = (
                        "https://docs.google.com/presentation/d/{id}/export"
                        "?format={format}".format(
                            id=gdrive_file_id,
                            format="pptx" if format is None else format,
                        )
                    )
                    continue
            elif (
                "Content-Disposition" in res.headers
                and res.headers["Content-Disposition"].endswith("pptx")
                and format not in {None, "pptx"}
            ):
                url = (
                    "https://docs.google.com/presentation/d/{id}/export"
                    "?format={format}".format(
                        id=gdrive_file_id,
                        format="pptx" if format is None else format,
                    )
                )
                continue

            if use_cookies:
                if not osp.exists(osp.dirname(cookies_file)):
                    os.makedirs(osp.dirname(cookies_file))
                with open(cookies_file, "w") as f:
                    cookies = [
                        (k, v)
                        for k, v in sess.cookies.items()
                        if not k.startswith("download_warning_")
                    ]
                    json.dump(cookies, f, indent=2)

            if "Content-Disposition" in res.headers:
                break
            if not (gdrive_file_id and is_gdrive_download_link):
                break

            try:
                url = self.get_url_from_gdrive_confirmation(res.text)
            except FileURLRetrievalError as e:
                message = (
                    "**Failed to retrieve file url:**\n\n```\n{}```\n\n"
                    "You may still be able to access the file from the browser:"
                    "\n\n\t{}\n\n"
                    "but I can't. Please check connections and permissions."
                ).format(
                    self.indent("\n".join(textwrap.wrap(str(e))), prefix="\t"),
                    url_origin,
                )
                raise FileURLRetrievalError(message)

        if gdrive_file_id and is_gdrive_download_link:
            content_disposition = six.moves.urllib_parse.unquote(
                res.headers["Content-Disposition"]
            )
            m = re.search(r"filename\*=UTF-8''(.*)", content_disposition)
            filename_from_url = m.groups()[0]
            filename_from_url = filename_from_url.replace(osp.sep, "_")
        else:
            filename_from_url = osp.basename(url)

        if output is None:
            output = filename_from_url

        output_is_path = isinstance(output, six.string_types)
        if output_is_path and output.endswith(osp.sep):
            if not osp.exists(output):
                os.makedirs(output)
            output = osp.join(output, filename_from_url)

        existing_tmp_files = []
        for file in os.listdir(osp.dirname(output) or "."):
            if file.startswith(osp.basename(output)):
                existing_tmp_files.append(osp.join(osp.dirname(output), file))
        if resume and existing_tmp_files:
            if len(existing_tmp_files) != 1:
                print(
                    "There are multiple temporary files to resume:",
                    file=sys.stderr,
                )
                print("\n")
                for file in existing_tmp_files:
                    print("\t", file, file=sys.stderr)
                print("\n")
                print(
                    "Please remove them except one to resume downloading.",
                    file=sys.stderr,
                )
                return
            tmp_file = existing_tmp_files[0]
        else:
            resume = False
            tmp_file = tempfile.mktemp(
                suffix=tempfile.template,
                prefix=osp.basename(output),
                dir=osp.dirname(output),
            )

        async with aiofiles.open(tmp_file, mode="ab") as f:
            headers = None

            if tmp_file is not None and (await f.tell()) != 0:
                headers = {"Range": "bytes={}-".format(await f.tell())}

            if not quiet:
                print("Downloading...", file=sys.stderr)
                if resume:
                    print("Resume:", tmp_file, file=sys.stderr)
                if url_origin != url:
                    print("From (original):", url_origin, file=sys.stderr)
                    print("From (redirected):", url, file=sys.stderr)
                else:
                    print("From:", url, file=sys.stderr)
                print(
                    "To:",
                    osp.abspath(output) if output_is_path else output,
                    file=sys.stderr,
                )

            try:
                async with sess.stream(
                    "GET",
                    url,
                    timeout=httpx.Timeout(180.0),
                    follow_redirects=True,
                    headers=headers if headers else sess.headers,
                ) as res:
                    total = res.headers.get("Content-Length")
                    if total is not None:
                        total = int(total)

                    if not quiet:
                        pbar = tqdm.tqdm(total=total, unit="B", unit_scale=True)

                    async for chunk in res.aiter_bytes():
                        await f.write(chunk)

                        if not quiet:
                            pbar.update(len(chunk))

                        if progress:
                            func = functools.partial(
                                progress,
                                res.num_bytes_downloaded,
                                total,
                                *progress_args
                            )

                            if inspect.iscoroutinefunction(progress):
                                await func()
                            else:
                                await self.loop.run_in_executor(self.executor, func)

                if not quiet:
                    pbar.close()
                if tmp_file:
                    await f.close()
                    shutil.move(tmp_file, output)
            finally:
                await sess.aclose()

        return output