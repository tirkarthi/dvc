import os
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional, TypedDict

from dvc.exceptions import PathMissingError

if TYPE_CHECKING:
    from dvc.fs.dvc import DvcFileSystem

    from . import Repo


class DiskUsageEntry(TypedDict):
    path: str
    isout: bool
    isdir: bool
    isexec: bool
    size: int


def du(
    url: str,
    path: Optional[str] = None,
    rev: Optional[str] = None,
    dvc_only: bool = False,
    summary: bool = True,
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
            "isout": bool,
            "isdir": bool,
            "isexec": bool,
            "size": int
        }
    """
    from . import Repo

    with Repo.open(url, rev=rev, subrepos=True, uninitialized=True) as repo:
        path = path or ""

        entries = list(_du(repo, path, dvc_only))

        # For summary single entry of folder and total size can be returned
        if summary:
            total_size = sum(entry.get("size", 0) for entry in entries)
            entries = [
                {
                    "path": url,
                    "isdir": True,
                    "isexec": False,
                    "isout": False,
                    "size": total_size,
                }
            ]
        else:
            entries.sort(key=lambda entry: entry["path"])

        return entries


def _calculate_size_from_dvc_info(dvc_info) -> int:
    size = 0
    for ((_, *_), (meta, *_)) in dvc_info.get("outs", []):
        if not meta:
            continue
        size += meta.size

    return size


def _calculate_size_from_folder(repo, folder) -> int:
    # For SCM folders the path is cloned to a temporary directory
    # Use the temporary directory value so that we can from there
    # to calculate size for a directory.
    if repo.scm:
        root_directory = Path(repo.scm._root_dir)
    else:
        root_directory = Path(repo.root_dir)

    folder = Path(folder)
    root = folder.root

    # For a folder path that starts "/" using it with root_dir will
    # make it the root path. Remove "/" to make the folder path relative
    # to root_dir
    if root == "/":
        absolute_path = Path(root_directory, *folder.parts[1:])
    else:
        absolute_path = Path(root_directory, folder)

    # https://stackoverflow.com/a/1392549/2610955
    return sum(
        f.stat().st_size for f in absolute_path.glob("**/*") if f.is_file()
    )


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
    repo: "Repo", path: str, dvc_only: bool = False
) -> Iterator[DiskUsageEntry]:

    infos = info_from_repo(dvc_only, path, repo, recursive=False)

    for name, info in infos.items():
        isdir = info["type"] == "directory"
        dvc_info = info.get("dvc_info", {})

        if dvc_info.get("outs") or not dvc_only:
            if not isdir:
                size = info.get("size", 0)
            else:
                size = _calculate_size(info)

            yield {
                "path": name,
                "isout": dvc_info.get("isout", False),
                "isdir": isdir,
                "size": size,
                "isexec": info.get("isexec", False),
            }
