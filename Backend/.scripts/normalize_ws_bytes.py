from pathlib import Path

root = Path(__file__).resolve().parent.parent
if (root / "backend").exists():
    targets = [
        root / "backend" / "server" / "backend_skeleton.py",
        root / "backend" / "app.py",
    ]
else:
    targets = [root / "server" / "backend_skeleton.py", root / "app.py"]

for p in targets:
    if not p.exists():
        continue
    b = p.read_bytes()
    # Normalize CRLF to LF
    b = b.replace(b"\r\n", b"\n")
    lines = b.split(b"\n")
    out_lines = []
    for line in lines:
        # if line only contains spaces or tabs, make it empty
        if line.strip(b" \t") == b"":
            out_lines.append(b"")
        else:
            # strip trailing spaces and tabs
            out_lines.append(line.rstrip(b" \t"))
    new_b = b"\n".join(out_lines)
    # Preserve trailing newline if original had one
    if b.endswith(b"\n") and not new_b.endswith(b"\n"):
        new_b += b"\n"
    if new_b != b:
        p.write_bytes(new_b)
        print(f"Fixed bytes whitespace: {p}")
print("done")