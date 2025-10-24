"""Strip trailing whitespace and normalize blank lines in .py files

This script rewrites .py files in the repo, removing trailing spaces and
replacing lines that contain only whitespace with empty lines.
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
files = list(root.rglob("*.py"))
for f in files:
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        continue
    changed = False
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if line.strip() == "":
            # blank line -> empty
            if line != "":
                changed = True
            new_lines.append("")
        else:
            # strip trailing spaces
            if line.rstrip() != line:
                changed = True
            new_lines.append(line.rstrip())
    new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")
    if changed:
        f.write_text(new_text, encoding="utf-8")
        print(f"Fixed whitespace: {f}")
print("Done")
