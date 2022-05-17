import io
import os
from contextlib import redirect_stdout, suppress

import pytest

from dvc.cli import main
from dvc.exceptions import PathMissingError
from dvc.repo import Repo


def test_du_repo(tmp_dir, dvc, scm):
    """Test du output for DVC repo."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": "baz"}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), summary=False)

    assert files == [
        {
            "path": ".dvcignore",
            "isout": False,
            "isdir": False,
            "size": 139,
            "isexec": False,
        },
        {
            "path": ".gitignore",
            "isout": False,
            "isdir": False,
            "size": 10,
            "isexec": False,
        },
        {
            "path": "bar",
            "isout": True,
            "isdir": False,
            "size": 3,
            "isexec": False,
        },
        {
            "path": "bar.dvc",
            "isout": False,
            "isdir": False,
            "size": 68,
            "isexec": False,
        },
        {
            "path": "foo",
            "isout": True,
            "isdir": False,
            "size": 3,
            "isexec": False,
        },
        {
            "path": "foo.dvc",
            "isout": False,
            "isdir": False,
            "size": 68,
            "isexec": False,
        },
    ]


def test_du_repo_summary(tmp_dir, dvc, scm):
    """Test du's summarized output for DVC repo."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": "baz"}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), summary=True)

    assert files == [
        {
            "path": os.fspath(tmp_dir),
            "isdir": True,
            "isexec": False,
            "isout": False,
            "size": 291,
        }
    ]


def test_du_scm(tmp_dir, dvc, scm):
    """Test SCM folder to du for size calculation."""

    tmp_dir.scm_gen({"foo": "bar", "bar": {"bar": "baz"}}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), summary=False)

    assert files == [
        {
            "isdir": False,
            "isexec": False,
            "isout": False,
            "path": ".dvcignore",
            "size": 139,
        },
        {
            "isdir": True,
            "isexec": False,
            "isout": False,
            "path": "bar",
            "size": 3,
        },
        {
            "isdir": False,
            "isexec": False,
            "isout": False,
            "path": "foo",
            "size": 3,
        },
    ]


def test_du_scm_path(tmp_dir, dvc, scm):
    """Test SCM folder with path supplied to du for size calculation."""

    tmp_dir.scm_gen({"foo": "bar", "bar": {"bar": "baz"}}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), path="bar/", summary=False)

    assert files == [
        {
            "path": "bar",
            "isout": False,
            "isdir": False,
            "size": 3,
            "isexec": False,
        }
    ]


def test_du_path(tmp_dir, dvc, scm):
    """Test path supplied to du."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": {"bar": "baz"}}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), path="bar/", summary=False)

    assert files == [
        {
            "path": "bar",
            "isout": True,
            "isdir": False,
            "size": 3,
            "isexec": False,
        },
    ]


def test_du_path_summary(tmp_dir, dvc, scm):
    """Test summary of path supplied to du."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": {"bar": "baz"}}, commit="dvc")
    files = Repo.du(os.fspath(tmp_dir), path="bar/", summary=True)

    assert files == [
        {
            "path": os.fspath(tmp_dir),
            "isdir": True,
            "isexec": False,
            "isout": False,
            "size": 3,
        }
    ]


def test_du_rev(tmp_dir, dvc, scm):
    """Test commit supplied to du gives proper output."""

    stage = tmp_dir.dvc_gen({"foo": "bar"}, commit="rev1")
    rev1 = stage[0].repo.scm.get_rev()
    rev1_expected = [
        {
            "path": os.fspath(tmp_dir),
            "isdir": True,
            "isexec": False,
            "isout": False,
            "size": 215,
        }
    ]

    files = Repo.du(os.fspath(tmp_dir), summary=True)
    assert files == rev1_expected

    tmp_dir.dvc_gen({"foo": "spam"}, commit="rev2")
    stage[0].repo.scm.get_rev()
    rev2_expected = [
        {
            "path": os.fspath(tmp_dir),
            "isdir": True,
            "isexec": False,
            "isout": False,
            "size": 216,  # Plus 1 since one additional character
        }
    ]

    files = Repo.du(os.fspath(tmp_dir), summary=True)
    assert files == rev2_expected

    # Check output with first revision
    files = Repo.du(os.fspath(tmp_dir), rev=rev1, summary=True)
    assert files == rev1_expected


@pytest.mark.parametrize(
    "human_readable,size", [(True, "3.1K"), (False, "3072")]
)
def test_du_human_readable(human_readable, size, tmp_dir, dvc, scm):
    """Test human readable output"""

    tmp_dir.scm_gen({"foo": "bar" * 1024}, commit="dvc")
    buf = io.StringIO()

    flags = []
    if human_readable:
        flags = ["-h"]

    with redirect_stdout(buf):
        assert main(["du", *flags, os.fspath(tmp_dir)]) == 0

    assert f"{size}       foo" in buf.getvalue()


def test_du_invalid_path_exception(tmp_dir, dvc, scm):
    """Test invalid path raises Exception."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": {"bar": "baz"}}, commit="dvc")

    with pytest.raises(PathMissingError):
        Repo.du(os.fspath(tmp_dir), path="invalid/")


def test_du_cli(tmp_dir, dvc, scm):
    """Test du output for DVC repo."""

    tmp_dir.dvc_gen({"foo": "bar", "bar": "baz"}, commit="dvc")
    assert main(["du", os.fspath(tmp_dir)]) == 0


def test_du_help_works(tmp_dir, dvc, scm):
    """Test du --help works since -h is overridden"""

    usage_lines = [
        "usage: dvc du [-q | -v] [--dvc-only] [--json] [--help] [-h] [--rev [<commit>]]",
        "[-s]",
        "url [path]",
    ]

    buf = io.StringIO()

    with redirect_stdout(buf):
        # Suppress SystemExit since argparse raises it for help
        with suppress(SystemExit):
            assert main(["du", "--help"]) == 0

    output_lines = [line.strip() for line in buf.getvalue().splitlines()]
    assert output_lines[:3] == usage_lines


def test_remote_fetch(tmp_dir, local_cloud, dvc, scm):
    """Test calculating file size from remote."""

    tmp_dir.dvc_gen({"bar": {"bar": "baz" * 10}}, commit="dvc")

    ret = main(["remote", "add", "upstream", local_cloud.url])
    ret = main(["push", "-r", "upstream"])

    # Remove file to trigger remote lookup.
    os.unlink(os.path.join(tmp_dir, "bar", "bar"))

    files = Repo.du(
        os.fspath(tmp_dir), summary=False, dvc_only=True, recursive=True
    )

    assert files == [
        {
            "isdir": False,
            "isexec": False,
            "isout": True,
            "path": "bar/bar",
            "size": 30,
        }
    ]
