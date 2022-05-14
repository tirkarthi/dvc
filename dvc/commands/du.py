import argparse
import logging

from dvc.cli import completion
from dvc.cli.command import CmdBaseNoRepo
from dvc.cli.utils import append_doc_link
from dvc.commands.ls.ls_colors import LsColors
from dvc.exceptions import DvcException
from dvc.ui import ui

logger = logging.getLogger(__name__)


def _prettify(entries, with_color=False):
    if with_color:
        ls_colors = LsColors()

        def fmt(entry):
            path = ls_colors.format(entry)
            return f"{entry['size']:<10} {path}"

    else:

        def fmt(entry):
            return f"{entry['size']} {entry['path']}"

    return [fmt(entry) for entry in entries]


class CmdDiskUsage(CmdBaseNoRepo):
    def run(self):
        from dvc.repo import Repo

        try:
            entries = Repo.du(
                self.args.url,
                self.args.path,
                rev=self.args.rev,
                dvc_only=self.args.dvc_only,
                summary=self.args.summary,
            )
            if self.args.json:
                ui.write_json(entries)
            elif entries:
                entries = _prettify(entries, with_color=True)
                ui.write("\n".join(entries))
            return 0
        except DvcException:
            logger.exception(f"failed to du '{self.args.url}'")
            return 1


def add_parser(subparsers, parent_parser):
    DISK_USAGE_HELP = (
        "Show size of repository contents, including files"
        " and directories tracked by DVC and by Git."
    )
    du_parser = subparsers.add_parser(
        "du",
        aliases=["du"],
        parents=[parent_parser],
        description=append_doc_link(DISK_USAGE_HELP, "du"),
        help=DISK_USAGE_HELP,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    du_parser.add_argument("url", help="Location of DVC repository")
    du_parser.add_argument(
        "--dvc-only", action="store_true", help="Show only DVC outputs."
    )
    du_parser.add_argument(
        "--json",
        "--show-json",
        action="store_true",
        help="Show output in JSON format.",
    )
    du_parser.add_argument(
        "--rev",
        nargs="?",
        help="Git revision (e.g. SHA, branch, tag)",
        metavar="<commit>",
    )
    du_parser.add_argument(
        "path",
        nargs="?",
        help="Path to directory within the repository to list outputs for",
    ).complete = completion.DIR
    du_parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Show summary for the folder.",
    )
    du_parser.set_defaults(func=CmdDiskUsage)
