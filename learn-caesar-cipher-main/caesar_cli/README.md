# caesar-cli

A polished command-line interface for experimenting with the classic Caesar cipher. The CLI pairs well with the educational material in the sibling `src/` folder and can be installed locally with `pipx` or `pip install -e .`.

## Features

- Encode or decode plain text with shifts from 1–25, plus a `--rot13` shortcut.
- Read input from the command line, stdin, or interactive prompt when nothing is provided.
- Optional alphabet mapping display for both lowercase and uppercase characters.
- Pure-Python implementation suitable for teaching, scripting, or adding to automation workflows.

## Quick start

```bash
pip install -e .
caesar -s 5 -e "hello"
caesar -s 5 -d "mjqqt"
echo "uryyb" | caesar --rot13
```

## Development

```bash
pip install -e .[dev]
pytest --cov
ruff check
mypy
```

## License

MIT License – see `../LICENSE`.
