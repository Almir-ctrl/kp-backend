Proxy audio server for Lion's Roar Karaoke Studio

This small Flask app provides a simple `/proxy-audio` endpoint used by the frontend to fetch external audio files (avoids browser CORS restrictions).

Files:
- proxy_audio.py - the Flask server implementation
- requirements.txt - Python dependencies

Run (Windows PowerShell):

```powershell
# create and activate venv (if not already)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python proxy_audio.py
```

Test with curl (from any terminal):

```powershell
# preflight
curl -i -X OPTIONS http://127.0.0.1:5000/proxy-audio

# proxy a remote mp3 and save to file
curl -i -X POST http://127.0.0.1:5000/proxy-audio -H "Content-Type: application/json" -d '{"url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"}' --output sample.mp3
```

Notes:
- The server sets `Access-Control-Allow-Origin: *` for development. In production, restrict allowed origins.
- This is intended for local development and testing only.

Troubleshooting (Windows / native dependencies):

- If `pip install -r requirements.txt` fails with a `blis` build error similar to:
	`error: [WinError 2] The system cannot find the file specified` and `ERROR: Failed building wheel for blis`, it means compiling native extensions failed on your system.

- Quick fixes tried and recommended:
	1. Upgrade packaging tools inside your virtualenv:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

	2. If package compilation still fails, install Visual Studio Build Tools (select "C++ build tools") or LLVM/Clang and ensure the compiler is on your PATH.

	3. Workaround: if you use Anaconda/Miniconda, install `blis` from conda-forge to avoid building from source:

```powershell
conda install -c conda-forge blis
```

- See `CHANGELOG.md` in this folder for a timestamped record of the issue and the exact commands run.
