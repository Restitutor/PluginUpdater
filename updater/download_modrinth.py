#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import pathlib
from collections.abc import Iterator
from typing import Literal, NewType, cast

import requests

logging.basicConfig(level=logging.INFO)

USER_AGENT = "AutoPlug 1.1"

PluginId = NewType("PluginId", str)
UpdateTime = NewType("UpdateTime", str)
PluginMap = dict[PluginId, UpdateTime]


Loader = Literal["paper", "velocity"]


def parseArgs() -> tuple[pathlib.PosixPath, Loader]:
    parser = argparse.ArgumentParser(
        description="Update local repository using modrinth repository.",
    )

    parser.add_argument(
        "--tar",
        type=pathlib.PosixPath,
        required=True,
        help="Path to the target directory.",
    )
    parser.add_argument(
        "--loader",
        choices=["paper", "velocity"],
        required=True,
        help="Pick loader for plugins.",
    )

    args = parser.parse_args()
    return args.tar.resolve(), args.loader


def get_latest_file(name: str, loader: Loader) -> str | None:
    # May need to cache the id -> Location
    url = f"https://api.modrinth.com/v2/project/{name}/version"
    versions = requests.get(url, timeout=10).json()

    for v in versions:  # Assuume sorted
        if loader in v["loaders"]:
            return v["files"][0]["url"]

    return None


async def check_plugin(name: str, loader: Loader) -> bool:
    """True if successful."""
    url = get_latest_file(name, loader)
    if url is None:
        print(f"No {loader} file found for {name}")
        return False

    try:
        p = await asyncio.create_subprocess_exec("wget", "-U", USER_AGENT, "-qN", url)
        await p.communicate()
        print(f"Downloaded modrinth {name}")
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return False
    else:
        return True


def check_all(plugins: Iterator[PluginId]) -> PluginMap:
    params = {"ids": json.dumps(sorted(plugins))}
    projects = requests.get(
        "https://api.modrinth.com/v2/projects",
        params=params,
        timeout=5,
    ).json()
    return {p["slug"]: p["updated"] for p in projects}


async def update_all(plugins: PluginMap, loader: Loader) -> tuple[PluginMap, bool]:
    any_new = False
    new_dates = check_all(iter(plugins.keys()))
    for slug, date in plugins.items():
        latest_date = new_dates.get(slug, "")
        if date == latest_date:
            print(f"{slug} is up to date.")
            continue

        if await check_plugin(slug, loader):
            any_new = True
            plugins[slug] = latest_date

    return plugins, any_new


async def main() -> None:
    path, loader = parseArgs()
    pathlib.os.chdir(path)

    try:
        with pathlib.Path("modrinth.csv").open(encoding="utf-8") as f:
            plugins = cast(
                "PluginMap",
                (
                    dict(
                        [
                            i.split(",")
                            for i in f.read().splitlines()
                            if i.count(",") == 1
                        ],
                    )
                ),
            )
    except FileNotFoundError:
        print("modrinth.csv not found in path.")
        return

    if not plugins:
        print("No plugins found in modrinth.csv.")
    plugins, any_new = await update_all(plugins, loader)
    if not any_new:
        print("No new updates.")
        return

    with pathlib.Path("modrinth.csv").open("w") as f:
        f.writelines(f"{slug},{date}\n" for slug, date in plugins.items())


if __name__ == "__main__":
    asyncio.run(main())
