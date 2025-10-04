#!/usr/bin/env python3
import argparse
import asyncio
import os
import pathlib
from collections.abc import Generator
from urllib.parse import urljoin

import aiohttp
from lxml import html

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def parseArgs() -> pathlib.PosixPath:
    parser = argparse.ArgumentParser(
        description="Update local repository using github or jenkins repository.",
    )

    parser.add_argument(
        "--tar",
        type=pathlib.PosixPath,
        required=True,
        help="Path to the target directory.",
    )

    return parser.parse_args().tar.resolve()


async def readHtml(url: str) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": url,
    }
    async with (
        aiohttp.ClientSession(headers=headers) as session,
        session.get(url, allow_redirects=True) as response,
    ):
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return await response.text()


def listJars(content: str) -> Generator[str]:
    assert content
    tree = html.fromstring(content)
    for j in tree.xpath(
        '//a[substring(@href, string-length(@href) - 3) = ".jar"]/@href',
    ):
        if not j.endswith("javadoc.jar") and not j.endswith("sources.jar"):
            yield j


async def updateDb(url: str, jar: str) -> None:
    # Always use wget -N
    # Then auto delete anything older (separate script)
    link = urljoin(url, jar)
    p = await asyncio.create_subprocess_exec("wget", "-U", USER_AGENT, "-qN", link)
    await p.communicate()


async def checkJenkins(url: str) -> None:
    if not url.endswith("/"):
        # Otherwise url join will silently fail and provide wrong url
        print(f"Invalid url {url}")
        return
    try:
        jars = set(listJars(await readHtml(url)))

        if "github.com" in url:
            jars = [j for j in jars if "releases/download" in j]
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return
    else:
        await asyncio.gather(*(updateDb(url, jar) for jar in jars))


async def main() -> None:
    os.chdir(parseArgs())

    try:
        text = pathlib.Path("jenkins.txt").read_text(encoding="utf-8")
        URLS = [i.strip() for i in text.splitlines() if i.strip()]
    except FileNotFoundError:
        print("jenkins.txt not found in path.")
    else:
        assert URLS
        await asyncio.gather(*(checkJenkins(url) for url in URLS))


if __name__ == "__main__":
    asyncio.run(main())
