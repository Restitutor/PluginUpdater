import os
import pathlib
from email.utils import parsedate_to_datetime

import aiohttp
from aiohttp.typedefs import CIMultiDictProxy

USER_AGENT = "AutoPlug 1.1"
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}


def set_cwd(path: pathlib.Path) -> None:
    """Change current working directory."""
    os.chdir(path)


def _emailDateToUnix(date: str) -> int:
    return int(parsedate_to_datetime(date).timestamp())


async def _getHeaders(url: str) -> CIMultiDictProxy:
    async with (
        aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session,
        session.head(url, allow_redirects=True) as response,
    ):
        if "java-archive" not in response.headers["Content-Type"]:
            print("WARNING", url, response.headers["Content-Type"])
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.headers


async def _getContent(url: str) -> tuple[bytes, str, str]:
    async with (
        aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session,
        session.get(url, allow_redirects=True) as response,
    ):
        if "java-archive" not in response.headers["Content-Type"]:
            print("WARNING", url, response.headers["Content-Type"])
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return (
            await response.content.read(),
            response.headers["Last-Modified"],
            str(response.url),
        )


async def shouldDownload(url: str, dest: pathlib.PosixPath) -> bool:
    """Download if file size or modified does not match."""
    if not dest.is_file():
        return True

    headers = await _getHeaders(url)
    contentLength = int(headers.get("Content-Length", 0))
    if contentLength and contentLength != dest.stat().st_size:
        return True

    return _emailDateToUnix(headers["Last-Modified"]) != int(dest.stat().st_mtime)


async def downloadFile(url: str, dest: pathlib.PosixPath) -> str:
    content, lastModified, url = await _getContent(url)
    dest.write_bytes(content)
    mtime = _emailDateToUnix(lastModified)
    os.utime(dest, (mtime, mtime))
    return url
