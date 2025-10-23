"""Command line entry point for the educational Caesar cipher CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, Sequence, cast

from importlib import metadata

from .core import decode, encode, mapping_pairs

try:
    __version__ = metadata.version("caesar-cli")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev
    __version__ = "0.0.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="caesar",
        description="Encode or decode text using the classic Caesar cipher.",
        epilog="Tip: omit TEXT and pipe input via stdin to work with files.",
    )

    shift_group = parser.add_mutually_exclusive_group(required=False)
    shift_group.add_argument(
        "-s",
        "--shift",
        type=int,
        help="Shift amount (1-25).",
    )
    shift_group.add_argument(
        "-r",
        "--rot13",
        action="store_true",
        help="Shortcut for --shift 13 in encode mode (ROT13).",
    )

    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        "-e",
        "--encode",
        action="store_true",
        help="Force encode mode (default).",
    )
    mode_group.add_argument(
        "-d",
        "--decode",
        action="store_true",
        help="Decode text instead of encoding.",
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Source text. If omitted, data is read from stdin or you will be prompted.",
    )
    parser.add_argument(
        "--show-mapping",
        action="store_true",
        help="Display the alphabet mapping table before output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Show project background information and exit.",
    )
    return parser


def _coerce_shift(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.rot13:
        return 13

    if args.shift is None:
        parser.error("one of --shift/-s or --rot13 must be provided")
    shift = cast(int, args.shift)
    if not 1 <= shift <= 25:
        parser.error("--shift must be in the range 1-25")
    return shift


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return cast(str, args.text)

    if not sys.stdin.isatty():
        return sys.stdin.read().rstrip("\n")

    try:
        return input("Text: ")
    except EOFError:  # pragma: no cover - interactive edge case
        return ""


def _format_mapping(lines: Iterable[tuple[str, str]]) -> str:
    left, right = zip(*lines)
    header = "    " + " ".join(left)
    mapped = "→   " + " ".join(right)
    return f"{header}\n{mapped}"


def _print_mapping(shift: int, encode_mode: bool) -> None:
    lower, upper = mapping_pairs(shift, encode=encode_mode)
    mode_str = "Encoding" if encode_mode else "Decoding"
    print(f"{mode_str} mapping (shift {shift}):")
    print("Lowercase:")
    print(_format_mapping(lower))
    print("Uppercase:")
    print(_format_mapping(upper))
    print("-" * 30)


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    cli_args: Sequence[str] | None = list(argv) if argv is not None else None
    args = parser.parse_args(cli_args)

    if args.about:
        print("Caesar CLI — educational Caesar cipher toolkit.")
        return 0

    shift = _coerce_shift(args, parser)
    encode_mode = not args.decode
    text = _resolve_text(args)

    if args.show_mapping:
        _print_mapping(shift, encode_mode)

    try:
        result = encode(text, shift) if encode_mode else decode(text, shift)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected failure path
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


__all__ = ["main"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
