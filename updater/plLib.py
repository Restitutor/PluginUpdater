#!/usr/bin/env python3
import pathlib
from collections.abc import Callable
from typing import TypedDict

from index_plugins import index_plugins
from versions import CustomVersion


class PluginItem(TypedDict):
    path: pathlib.PosixPath
    version: CustomVersion


def _olderPluginFirst(
    one: PluginItem,
    two: PluginItem,
) -> tuple[PluginItem, PluginItem]:
    if firstMoreRecent(one, two):
        return two, one

    return one, two


def firstMoreRecent(srcPlugin: PluginItem, tarPlugin: PluginItem) -> bool:
    if srcPlugin["version"] < tarPlugin["version"]:
        return False

    if srcPlugin["version"] > tarPlugin["version"]:
        return True

    # Otherwise compare metadata and contents
    sp = srcPlugin["path"]
    tp = tarPlugin["path"]

    if sp.stat().st_mtime <= tp.stat().st_mtime:
        return False

    if sp.stat().st_size == tp.stat().st_size:
        return False

    return sp.read_bytes() != tp.read_bytes()


def getPluginDb(
    plPath: pathlib.PosixPath,
    promptDelete: None | Callable[[PluginItem, PluginItem], None],
    autoDeleteOld: bool,
) -> dict[str, PluginItem]:
    plugindb = {}
    for path, artifact, ymlVersion in index_plugins(plPath):
        # More edge cases to work on
        version = CustomVersion(ymlVersion)
        pli: PluginItem = {"path": path, "version": version}
        # Deduplicate
        if artifact in plugindb:
            older, newer = _olderPluginFirst(plugindb[artifact], pli)
            if autoDeleteOld:
                print(
                    f"Deleted old version: {older['path']} {older['version']} Kept: {newer['path']} {newer['version']}",
                )
                older["path"].unlink()
            elif promptDelete:
                promptDelete(older, newer)

            plugindb[artifact] = newer  # Always store newer
        else:
            plugindb[artifact] = pli

    if not plugindb:
        msg = f"No plugins found in {plPath}"
        raise FileNotFoundError(msg)

    return plugindb


def testVersion(
    plPath: pathlib.PosixPath,
) -> list[str]:
    errors = []
    assert plPath.is_dir()
    for path, artifact, ymlVersion in index_plugins(plPath):
        try:
            print(path, artifact, ymlVersion)
            print("Parsed successfully", CustomVersion(ymlVersion))
        except Exception:
            errors.append(ymlVersion)

    return errors
