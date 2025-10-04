#!/usr/bin/env python3
import argparse
import pathlib
import subprocess
import sys
from typing import Literal

import requests

USER_AGENT = "server-updater (discord.gg/JrhYskAFtA)"
BASE_API_URL = "https://fill.papermc.io/v3/projects"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

ServerType = Literal["paper", "velocity"]


class PaperMCAPIError(Exception):
    """Custom exception for PaperMC API errors."""


def get_latest_stable_build(serverType: ServerType, version: str) -> dict[str, str]:
    """Get the latest stable build information."""
    response = session.get(f"{BASE_API_URL}/{serverType}/versions/{version}/builds")

    try:
        builds = response.json()
    except requests.exceptions.JSONDecodeError as e:
        msg = f"Invalid JSON response from builds API: {response.content}"
        raise PaperMCAPIError(
            msg,
        ) from e

    # Find the first stable build (builds are ordered newest first)
    stable_build = None
    for build in builds:
        if build.get("channel") == "STABLE":
            stable_build = build
            break

    if not stable_build:
        msg = f"No stable build found for {serverType} version {version}"
        raise PaperMCAPIError(
            msg,
        )

    # Get download information
    server_download = stable_build.get("downloads", {}).get("server:default")
    if not server_download:
        msg = f"No server download available for build {stable_build['build']}"
        raise PaperMCAPIError(
            msg,
        )

    return {
        "build": str(stable_build["id"]),
        "filename": server_download["name"],
        "download_url": server_download["url"],
    }


def get_filename(serverType: ServerType, version: str, build: str) -> str:
    """Generate filename for the server jar."""
    return f"{serverType}-{version}-{build}.jar"


def download_server_jar(
    download_url: str,
    filename: str,
    server_path: pathlib.PosixPath,
) -> None:
    """Download the server jar file."""
    subprocess.run(
        ["wget", "-O", filename, download_url],
        check=True,
        cwd=str(server_path),
    )


def update_server(
    serverType: ServerType,
    version: str,
    serverPath: pathlib.PosixPath,
) -> None:
    """Update server jar to the latest stable build."""
    try:
        # Get latest stable build information
        build_info = get_latest_stable_build(serverType, version)
        latest_build = build_info["build"]
        filename = build_info["filename"]
        download_url = build_info["download_url"]

        # Check existing jars
        jars = list(serverPath.glob(f"{serverType}-*-*.jar"))

        # Remove old versions and check if we already have the latest
        found_current = False
        for jar_file in jars:
            if jar_file.name == filename:
                found_current = True
            else:
                jar_file.unlink()

        if found_current:
            print(f"No update for {serverType} {version} found.")
            return

        # Download the new version
        print(f"Downloading {serverType} {version} build {latest_build}...")
        download_server_jar(download_url, filename, serverPath)

        print(f"Successfully updated {serverType} to build {latest_build}")

    except PaperMCAPIError as e:
        print(f"Error updating server: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Download failed: {e}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update server jars using Fill v3 API.",
    )

    parser.add_argument(
        "type",
        type=str,
        choices=["paper", "velocity"],
        help="Type of server: paper or velocity",
    )
    parser.add_argument("version", type=str, help="Server version")
    parser.add_argument("path", type=pathlib.PosixPath, help="Path to server folder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    update_server(args.type, args.version, args.path.resolve())


if __name__ == "__main__":
    main()
