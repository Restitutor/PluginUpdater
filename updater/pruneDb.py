#!/usr/bin/env python3
import argparse
import pathlib

from plLib import getPluginDb


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update local repository using jenkins repository.",
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

    return parser.parse_args()


def main() -> None:
    args = parseArgs()
    getPluginDb(args.tar.resolve(), promptDelete=None, autoDeleteOld=not args.n)


if __name__ == "__main__":
    main()
