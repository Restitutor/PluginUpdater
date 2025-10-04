#!/usr/bin/env python3
import argparse
import logging
import pathlib
import subprocess
from collections.abc import Generator
from datetime import datetime

from lib.types.logevents import PluginUpdate
from plLib import PluginItem, firstMoreRecent, getPluginDb

psync_logger = logging.getLogger(__name__)


def mtimeToDateString(mtime: float) -> str:
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update plugins using a local repository.",
    )

    parser.add_argument(
        "--src",
        type=pathlib.PosixPath,
        required=True,
        help="Path to the source directory.",
    )
    parser.add_argument(
        "--tar",
        type=pathlib.PosixPath,
        required=True,
        help="Path to the target directory.",
    )
    parser.add_argument(
        "-n",
        action="store_true",
        help="Dry run. Does not change files.",
    )
    parser.add_argument(
        "-y",
        action="store_true",
        help="Confirm operation without prompting.",
    )

    return parser.parse_args()


def promptDelete(older: PluginItem, newer: PluginItem) -> None:
    print(
        f"WARNING. Duplicate plugin found. Older one at {older['path']} {older['version']}",
    )
    print(
        "Do you want to delete",
        older["path"].name,
        "and keep",
        newer["path"].name + "? (y/n)",
    )
    if input().lower().startswith("y"):
        older["path"].unlink()


def validateArgs(src: pathlib.PosixPath, tar: pathlib.PosixPath) -> None:
    for pdir in src, tar:
        if not pdir.exists():
            msg = f"The source path {pdir} does not exist or is not a directory."
            raise FileNotFoundError(
                msg,
            )

    if tar.name != "plugins":
        msg = "Not a valid plugin destination."
        raise Exception(msg)


DeltaGen = Generator[tuple[PluginItem, PluginItem]]


def getDelta(
    src: pathlib.PosixPath,
    tar: pathlib.PosixPath,
    autoyes: bool,
    skip_major: bool = True,
) -> DeltaGen:
    prompt = None if autoyes else promptDelete

    srcdb = getPluginDb(src, promptDelete=prompt, autoDeleteOld=False)
    tardb = getPluginDb(tar, promptDelete=prompt, autoDeleteOld=False)

    for artifact, srcPlugin in srcdb.items():
        if artifact not in tardb:
            continue

        tarPlugin = tardb[artifact]
        if not firstMoreRecent(srcPlugin, tarPlugin):
            continue

        if srcPlugin["version"].is_major_upgrade(tarPlugin["version"]) and skip_major:
            print("Skip major version upgrade", srcPlugin, tarPlugin)
            continue

        yield srcPlugin, tardb[artifact]


def updatePlugins(
    deltaGen: DeltaGen,
    dryrun: bool,
    autoyes: bool,
) -> tuple[PluginUpdate, ...]:
    updates: list[PluginUpdate] = []
    for srcPlugin, tarPlugin in deltaGen:
        if dryrun:
            print(
                "Would replace",
                tarPlugin["path"].stem,
                str(tarPlugin["version"]),
                "with",
                str(srcPlugin["version"]),
            )
            continue

        if not autoyes:
            print(
                "Replace",
                tarPlugin["path"].stem,
                str(tarPlugin["version"]),
                "with",
                str(srcPlugin["version"]) + "? (y/n)",
            )
            if not input().lower().startswith("y"):
                print("Skipping", tarPlugin["path"].stem)
                continue

        print(
            "Replaced",
            tarPlugin["path"].stem,
            str(tarPlugin["version"]),
            "with",
            str(srcPlugin["version"]),
        )
        try:
            try:
                oldTime = mtimeToDateString(tarPlugin["path"].stat().st_mtime)
            except FileNotFoundError:
                oldTime = None

            tarPlugin["path"].unlink()
            dest = str(tarPlugin["path"].parent / srcPlugin["path"].name)
            subprocess.run(
                (
                    "cp",
                    "--reflink=auto",
                    "--preserve=timestamps",
                    str(srcPlugin["path"]),
                    dest,
                ),
                check=True,
            )
        except Exception:
            print(f"Failed to update plugin {tarPlugin['path'].stem}")
        else:
            oldVersion = str(tarPlugin["version"])
            newVersion = str(srcPlugin["version"])

            if oldVersion == newVersion:
                if oldTime is not None:
                    oldVersion += " " + oldTime
                newVersion += " " + mtimeToDateString(srcPlugin["path"].stat().st_mtime)

            updates.append(
                {
                    "name": tarPlugin["path"].stem,
                    "newVersion": newVersion,
                    "oldVersion": oldVersion,
                },
            )

    return tuple(updates)


def main() -> None:
    args = parseArgs()
    src = args.src.resolve()
    target = args.tar.resolve()
    validateArgs(src, target)
    updates = updatePlugins(getDelta(src, target, args.y), args.n, args.y)

    if updates:
        print(f"Completed {len(updates)} plugin updates for {target.parent.name}.")
    else:
        print("[PSYNC] No updates done.")
        return


if __name__ == "__main__":
    main()
