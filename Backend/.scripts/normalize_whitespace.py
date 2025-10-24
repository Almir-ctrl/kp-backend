"""Normalize whitespace for a list of files.

Removes trailing spaces, converts whitespace-only lines to empty lines,
and ensures exactly two blank lines before top-level '@app.route'
decorators.
"""
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
# prefer backend/ layout if present (Lion-s-Roar-Studio/backend)
targets = []
if (repo / "backend").exists():
    targets = [
        repo / "backend" / "server" / "backend_skeleton.py",
        repo / "backend" / "app.py",
    ]
else:
    targets = [repo / "server" / "backend_skeleton.py", repo / "app.py"]

for f in targets:
    if not f.exists():
        continue
    text = f.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Strip trailing whitespace and normalize blank lines
    new_lines = [line.rstrip() for line in lines]
    # Convert whitespace-only lines to empty
    new_lines = [line if line.strip() != "" else "" for line in new_lines]
    # Ensure two blank lines before decorators
    out = []
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        if line.lstrip().startswith("@app.route"):
            # remove extra blank lines before
            # ensure there are exactly two blank lines before this line in out
            while len(out) > 0 and out[-1] == "":
                out.pop()
            # add two blank lines
            out.append("")
            out.append("")
            out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    if new_text != text:
        f.write_text(new_text, encoding="utf-8")
        print(f"Normalized whitespace: {f}")
print("Done")
