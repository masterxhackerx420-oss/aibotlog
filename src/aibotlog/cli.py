"""Command-line entry point for aibotlog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aibotlog import __version__
from aibotlog.core import dumps_report, render_report, scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aibotlog",
        description=(
            "Count AI crawler hits and AI-answer referrals in nginx or apache "
            "combined access logs."
        ),
    )
    parser.add_argument(
        "logs",
        nargs="*",
        help="access log files (plain or .gz). omit or use - to read stdin.",
    )
    parser.add_argument(
        "--by",
        choices=("day", "path"),
        help="limit the breakdown to days or paths (default: both)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="number of top paths to show (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print JSON instead of tables",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be a positive integer")

    logs = list(args.logs)
    if not logs:
        if sys.stdin.isatty():
            parser.error("provide an access log file, or pipe logs on stdin")
        logs = ["-"]

    for path in logs:
        if path != "-" and not Path(path).is_file():
            print(f"aibotlog: no such file: {path}", file=sys.stderr)
            return 2

    try:
        report = scan(logs)
    except OSError as exc:
        print(f"aibotlog: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        sys.stdout.write(dumps_report(report, by=args.by, top=args.top))
    else:
        sys.stdout.write(render_report(report, by=args.by, top=args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
