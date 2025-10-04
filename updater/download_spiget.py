#!/usr/bin/env python3
import argparse
import asyncio
import logging
import pathlib

from downloadLib import downloadFile, set_cwd, shouldDownload

logger = logging.getLogger(__name__)


def parseArgs() -> pathlib.PosixPath:
    parser = argparse.ArgumentParser(
        description="Update local repository using spiget repository.",
    )

    parser.add_argument(
        "--tar",
        type=pathlib.PosixPath,
        required=True,
        help="Path to the target directory.",
    )

    return parser.parse_args().tar.resolve()


async def checkSpiget(name: str, rid: str) -> None:
    # May need to cache the id -> Location
    url = f"https://api.spiget.org/v2/resources/{rid}/download"
    try:
        assert rid
        assert int(rid)
        dest = pathlib.PosixPath(f"{name}.jar")
        if not await shouldDownload(url, dest):
            print(f"{name} is up to date.")
            return

        await downloadFile(url, dest)
        print(f"Downloaded {name}")
    except Exception as e:
        print(f"Error fetching {rid}: {e}")


async def main() -> None:
    set_cwd(parseArgs())

    try:
        with pathlib.Path("spiget.csv").open(encoding="utf-8") as f:
            args = [i.split(",") for i in f.read().splitlines() if i.count(",") == 1]
    except FileNotFoundError:
        print("spiget.csv not found in path.")
    else:
        assert args
        await asyncio.gather(*(checkSpiget(*arg) for arg in args))


if __name__ == "__main__":
    asyncio.run(main())
