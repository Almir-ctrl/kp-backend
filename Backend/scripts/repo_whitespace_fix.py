"""Small repo-wide whitespace and blank-line normalizer.

Runs over .py files (excluding .venv, outputs, node_modules and a few scripts)
and trims trailing spaces, ensures a single newline at EOF, and collapses
multiple trailing blank lines.
"""
from pathlib import Path
import sys
from typing import Set

EXCLUDE_DIRS: Set[str] = {".venv", "outputs", "node_modules", "server/scripts", ".scripts"}


def normalize_file(path: Path) -> bool:
    """Normalize a single file. Returns True if modified."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        # Could be a permissions issue or binary file mistakenly named .py
        return False

    # Preserve existing newline handling when splitting
    lines = text.splitlines(True)

    # Remove trailing whitespace from each line and ensure newline ending
    new_lines = [line.rstrip() + "\n" for line in lines]

    # Collapse excessive trailing blank lines
    while len(new_lines) > 1 and new_lines[-1].strip() == "":
        new_lines.pop()

    # Ensure final newline exists
    if not new_lines:
        new_lines = ["\n"]

    if not new_lines[-1].endswith("\n"):
        new_lines[-1] = new_lines[-1] + "\n"

    if new_lines != lines:
        try:
            path.write_text("".join(new_lines), encoding="utf-8")
        except Exception:
            return False
        return True

    return False


def main(root: str = ".") -> int:
    modified = 0
    root_path = Path(root)
    for path in root_path.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if normalize_file(path):
            modified += 1

    # Use a single, clear status line for machine- and human-readable output
    print("Normalized {} files".format(modified))
    return 0


if __name__ == "__main__":
    sys.exit(main("."))
