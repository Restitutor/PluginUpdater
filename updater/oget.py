#!/usr/bin/env python3
import argparse
import asyncio
import logging
import pathlib

from downloadLib import downloadFile, shouldDownload

log = logging.getLogger(__name__)


def parseArgs() -> tuple[str, pathlib.PosixPath]:
    parser = argparse.ArgumentParser(
        description="Download a file from a URL if it has been updated.",
    )
    parser.add_argument("url", type=str, help="The URL to download from.")
    parser.add_argument(
        "-O",
        dest="output",
        type=pathlib.PosixPath,
        required=True,
        help="The output file path.",
    )
    args = parser.parse_args()

    # Validate that the URL starts with https
    if not args.url.startswith("https://"):
        parser.error("The URL must start with 'https://'")

    return args.url, args.output.resolve()


def getLastNumber(url: str) -> int:
    # Split the URL by slashes and filter out non-integer parts
    for part in reversed(url.split("/")):
        if part.isdigit():
            return int(part)
    msg = "No integer found in the URL"
    raise ValueError(msg)


async def main() -> None:
    url, dest = parseArgs()

    if not await shouldDownload(url, dest):
        print(f"{dest.stem} is up to date.")
        return

    trueUrl = await downloadFile(url, dest)
    print(f"Downloaded {dest.stem} from {trueUrl}")
    try:
        version = getLastNumber(trueUrl)
        print(f"File version: {version}")
    except ValueError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
