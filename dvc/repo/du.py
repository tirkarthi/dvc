import os
from itertools import chain
from typing import TYPE_CHECKING, Any, Iterator, Optional, TypedDict

from dvc.exceptions import PathMissingError

if TYPE_CHECKING:
    from dvc.fs.data import DataFileSystem
    from dvc.fs.dvc import DvcFileSystem

    from . import Repo


class DiskUsageEntry(TypedDict):
    path: str
    isdir: bool
    size: int


def du(
    url: str,
    path: Optional[str] = None,
    rev: Optional[str] = None,
    dvc_only: bool = False,
    summary: bool = True,
    recursive: bool = False,
) -> list[DiskUsageEntry]:
    """Methods for retrieving size of files and outputs for the repo.

    Args:
        url (str): the repo url
        path (str, optional): relative path into the repo
        rev (str, optional): SHA commit, branch or tag name
        dvc_only (bool, optional): show only DVC-artifacts

    Returns:
        list of `DiskUsageEntry`

    Notes:
        `entry` is a dictionary with structure
        {
            "path": str,
            "isdir": bool,
            "size": int
        }
    """
    from . import Repo

    with Repo.open(url=url, rev=rev) as repo:
        path = path or ""

        entries = list(_du(repo, path, dvc_only, recursive))

        # For summary single entry of folder and total size can be returned
        if summary:
            total_size = sum(entry.get("size", 0) for entry in entries)
            entries = [
                {
                    "path": path or url,
                    "isdir": True,
                    "size": total_size,
                }
            ]
        else:
            entries.sort(key=lambda entry: entry["path"])

        return entries


def _calculate_size_from_dvc_info(dvc_info) -> int:
    size = 0
    for (_, (meta, *_)) in dvc_info.get("outs", []):
        if not meta:
            continue
        size += meta.size

    return size


def _calculate_size_from_folder(repo, folder) -> int:
    if folder.startswith("/"):
        folder = folder[1:]

    return repo.fs.du(folder, total=True)


def _calculate_size(info) -> int:
    dvc_info = info.get("dvc_info")

    if dvc_info:
        return _calculate_size_from_dvc_info(dvc_info)

    return _calculate_size_from_folder(info["repo"], info["name"])


def info_from_repo(
    dvc_only: bool, path: str, repo: "Repo", recursive: bool
) -> dict[str, dict[str, Any]]:
    fs: "DvcFileSystem" = repo.dvcfs
    fs_path = fs.from_os_path(path)

    try:
        fs_path = fs.info(fs_path)["name"]
    except FileNotFoundError:
        raise PathMissingError(path, repo, dvc_only=dvc_only)

    infos = {}
    for root, dirs, files in fs.walk(
        fs_path, dvcfiles=True, dvc_only=dvc_only
    ):
        entries = chain(files, dirs) if not recursive else files

        for entry in entries:
            entry_fs_path = fs.path.join(root, entry)
            relparts = fs.path.relparts(entry_fs_path, fs_path)
            name = os.path.join(*relparts)
            infos[name] = fs.info(entry_fs_path)

        if not recursive:
            break

    if not infos and fs.isfile(fs_path):
        infos[os.path.basename(path)] = fs.info(fs_path)

    return infos


def _du(
    repo: "Repo", path: str, dvc_only: bool = False, recursive: bool = False
) -> Iterator[DiskUsageEntry]:

    data_fs: "DataFileSystem" = repo.datafs
    infos = info_from_repo(dvc_only, path, repo, recursive=recursive)

    for name, info in infos.items():
        isdir = info["type"] == "directory"
        dvc_info = info.get("dvc_info", {})

        if dvc_info.get("outs") or not dvc_only:
            if not isdir:
                size = info.get("size", 0)
                if size is None:
                    path = info["name"]
                    size = data_fs.size(path)
            else:
                size = _calculate_size(info)

            yield {
                "path": name,
                "isdir": isdir,
                "size": size,
            }
