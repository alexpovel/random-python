#!/usr/bin/env python3

"""Apply one of the commands to all applicable server components in correct order."""


import argparse
from typing import Dict

from control.docker.compose import COMMANDS, CommandMetadata, Server
from control.util.files import PROJECT_ROOT
from control.util.misc import pprint


def cli_parse(choices: Dict[str, CommandMetadata]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "command",
        help="Choose from:\n"
        + pprint({cmd: meta.desc for cmd, meta in choices.items()}),
        choices=choices,
        metavar="command",
    )
    parser.add_argument(
        "remainder",
        # For an overview of `nargs`, see also https://stackoverflow.com/a/31243133/11477374
        nargs=argparse.REMAINDER,
        help="Remainder (subcommands and flags) to be passed on to the subcommand.",
    )
    return parser.parse_args()


def main():
    args = cli_parse(choices=COMMANDS)
    server = Server(PROJECT_ROOT, args.command)
    server.run(args.remainder)


if __name__ == "__main__":
    main()
