"""Command line entry point for the advanced Caesar cipher CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Iterable, Sequence, Tuple, cast

from . import __version__
from .core import decode, encode, mapping_pairs

Printer = Callable[[str], None]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="caesar",
        description="Encode or decode text using the classic Caesar cipher.",
        epilog="Tip: omit TEXT and pipe input via stdin to work with files.",
    )

    shift_group = parser.add_mutually_exclusive_group(required=False)
    shift_group.add_argument("-s", "--shift", type=int, help="Shift amount (1-25).")
    shift_group.add_argument(
        "-r",
        "--rot13",
        action="store_true",
        help="Shortcut for --shift 13 in encode mode (ROT13).",
    )

    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument("-e", "--encode", action="store_true", help="Force encode mode (default).")
    mode_group.add_argument("-d", "--decode", action="store_true", help="Decode text instead of encoding.")

    parser.add_argument(
        "text",
        nargs="?",
        help="Source text. If omitted, data is read from stdin or you will be prompted.",
    )
    parser.add_argument("--show-mapping", action="store_true", help="Display the alphabet mapping table before output.")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output (auto-disabled when piping).")
    parser.add_argument("--input", type=str, help="Read text from file instead of the TEXT argument or stdin.")
    parser.add_argument("--output", type=str, help="Write result to file instead of stdout (overwrites).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--about", action="store_true", help="Show project information and exit.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    cli_args: Sequence[str] | None = list(argv) if argv is not None else None
    args = parser.parse_args(cli_args)

    printer, color_enabled = _get_printer(not args.no_color and sys.stdout.isatty())

    if args.about:
        printer("Caesar CLI — educational command-line tool for the Caesar cipher.")
        printer("Repository: https://github.com/jguida941/caesar_cipher")
        printer(f"Version: {__version__}")
        return 0

    if args.input and args.text is not None:
        parser.error("Specify either TEXT or --input, not both.")

    if (
        args.text is None
        and args.input is None
        and args.shift is None
        and not args.rot13
        and sys.stdin.isatty()
    ):
        return repl(default_shift=3, show_mapping=args.show_mapping, color_enabled=color_enabled)

    shift = _coerce_shift(args, parser)
    encode_mode = not args.decode

    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:  # pragma: no cover - filesystem errors
            print(f"Error reading {args.input}: {exc}", file=sys.stderr)
            return 1
    else:
        text = _resolve_text(args)

    if args.show_mapping:
        _print_mapping(shift, encode_mode, printer, color_enabled)

    try:
        result = encode(text, shift) if encode_mode else decode(text, shift)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected failure path
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(result)
        except OSError as exc:  # pragma: no cover - filesystem errors
            print(f"Error writing {args.output}: {exc}", file=sys.stderr)
            return 1
    else:
        printer(result)

    return 0


def repl(
    default_shift: int = 3,
    show_mapping: bool = False,
    *,
    color_enabled: bool = False,
) -> int:
    """Interactive REPL for the Caesar CLI."""

    printer, rich_enabled = _get_printer(color_enabled)
    last_shift = default_shift
    mapping_enabled = show_mapping

    try:
        while True:
            mode = input("Mode [e=encode, d=decode, r=rot13, q=quit]: ").strip().lower()
            if not mode:
                mode = "e"

            if mode == "q":
                printer("Goodbye!")
                return 0

            if mode not in {"e", "d", "r"}:
                printer("Unknown option. Choose e, d, r, or q.")
                continue

            if mode == "r":
                shift = 13
                encode_mode = True
            else:
                shift_input = input(f"Shift (1–25) [default: {last_shift}]: ").strip()
                if not shift_input:
                    shift = last_shift
                else:
                    try:
                        shift = int(shift_input)
                        if not 1 <= shift <= 25:
                            raise ValueError
                    except ValueError:
                        printer("Shift must be an integer between 1 and 25.")
                        continue
                encode_mode = mode != "d"

            text = input("Text (empty to cancel): ")
            if not text:
                printer("Cancelled.")
                continue

            try:
                result = encode(text, shift) if encode_mode else decode(text, shift)
            except (TypeError, ValueError) as exc:
                printer(f"Error: {exc}")
                continue

            if mapping_enabled:
                _print_mapping(shift, encode_mode, printer, rich_enabled)

            mode_label = "encode" if encode_mode else "decode"
            printer(f"Result ({mode_label}, shift {shift}): {result}")

            if mode != "r":
                last_shift = shift

            follow_up = input("Again? [Enter=yes, q=quit, m=toggle mapping]: ").strip().lower()
            if follow_up == "q":
                return 0
            if follow_up == "m":
                mapping_enabled = not mapping_enabled
                status = "enabled" if mapping_enabled else "disabled"
                printer(f"Mapping display {status}.")
    except (KeyboardInterrupt, EOFError):  # pragma: no cover - user interruption
        printer("")
        return 0


def _get_printer(wants_color: bool) -> Tuple[Printer, bool]:
    if wants_color:
        try:
            from rich.console import Console as RichConsole
        except ImportError:
            rich_console = None
        else:
            rich_console = RichConsole()
            return cast(Printer, rich_console.print), True

    def plain_print(message: str = "", **_: object) -> None:
        print(message)

    return plain_print, False


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


def _print_mapping(
    shift: int,
    encode_mode: bool,
    printer: Printer,
    rich_enabled: bool,
) -> None:
    lower, upper = mapping_pairs(shift, encode=encode_mode)
    mode_str = "Encoding" if encode_mode else "Decoding"
    if rich_enabled:
        printer(f"[bold cyan]{mode_str} mapping[/] (shift {shift}):")
        printer("[italic]Lowercase:[/]")
    else:
        printer(f"{mode_str} mapping (shift {shift}):")
        printer("Lowercase:")
    printer(_format_mapping(lower))
    printer("Uppercase:")
    printer("-" * 30)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
