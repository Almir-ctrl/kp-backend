from pathlib import Path

root = Path(".").resolve()
# Prefer host repo layout with capitalized Backend directory. Fall back to
# lowercase 'backend' if present, then to repository root layout.
if (root / "Backend").exists():
    files = [
        Path("Backend/server/backend_skeleton.py"),
        Path("Backend/app.py"),
    ]
elif (root / "backend").exists():
    files = [
        Path("backend/server/backend_skeleton.py"),
        Path("backend/app.py"),
    ]
else:
    files = [Path("server/backend_skeleton.py"), Path("app.py")]
for f in files:
    if not f.exists():
        continue
    text = f.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "" and line != "":
            # display repr to see whitespace
            print(f"{f}:{i}: {repr(line)}")
print("done")
