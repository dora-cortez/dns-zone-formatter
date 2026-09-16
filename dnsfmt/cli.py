import argparse
import sys

from .records import ZoneSyntaxError, format_record, parse_line


def iter_lines(paths):
    if not paths or paths == ["-"]:
        for line in sys.stdin:
            yield line.rstrip("\n")
        return
    for path in paths:
        with open(path) as f:
            for line in f:
                yield line.rstrip("\n")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dnsfmt",
        description="Normalize messy DNS zone file records into consistent, aligned output.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="zone files to format; omit, or pass '-', to read from stdin",
    )
    parser.add_argument(
        "--default-ttl",
        type=int,
        default=3600,
        help="TTL to apply when a record omits one (default: 3600)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    last_name = None
    exit_code = 0
    for lineno, raw in enumerate(iter_lines(args.files), start=1):
        try:
            record, last_name = parse_line(raw, last_name, args.default_ttl)
        except ZoneSyntaxError as exc:
            print(f"dnsfmt: line {lineno}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        if record is None:
            continue
        print(format_record(record))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
