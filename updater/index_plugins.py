#!/usr/bin/env python3
import argparse
import json
import pathlib
from collections.abc import Generator
from zipfile import ZipFile

PluginGen = Generator[tuple[pathlib.PosixPath, str, str]]


def get_prop(contents: str, is_yml: bool, prop: str) -> str:
    if is_yml:
        prefix = f"{prop}: "
        for line in contents.splitlines():
            if line.startswith(prefix):
                return line.split(prefix)[-1].strip("'").strip('"')
    else:
        return json.loads(contents)[prop]

    raise ValueError


def read_plugin_yml(jar_file: pathlib.PosixPath) -> tuple[str, bool]:
    with ZipFile(jar_file, "r") as zip_ref:
        for p in "plugin.yml", "paper-plugin.yml", "velocity-plugin.json":
            try:
                with zip_ref.open(p) as file:
                    pack = file.read()
                    return pack.decode("utf-8"), p.endswith(".yml")
            except KeyError:
                continue

    raise FileNotFoundError


def index_plugins(folder: pathlib.PosixPath) -> PluginGen:
    """Extracts and prints the contents of plugin.yml from each .jar file provided.

    :param jar_files: List of paths to .jar files
    """
    assert folder.is_dir()

    for jar_file in sorted(folder.glob("*jar")):
        try:
            text, is_yml = read_plugin_yml(jar_file)
            artifact = get_prop(text, is_yml, "main")
            version = get_prop(text, is_yml, "version")
            yield jar_file, artifact, version
        except (KeyError, FileNotFoundError):
            print(f"plugin.yml paper-plugin.yml not found in {jar_file}")
        except Exception as e:
            print(f"An error occurred with {jar_file}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List plugins in a path.")
    parser.add_argument("path", type=pathlib.PosixPath, help="Path to plugins/ folder")
    directory = parser.parse_args().path

    gen = index_plugins(directory)
    for jar, artifact, version in gen:
        print(jar, artifact, version)


if __name__ == "__main__":
    main()
