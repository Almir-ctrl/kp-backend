import hashlib
import os

files = [
    'requirements-optional.txt',
    'scripts/install_optional_deps.ps1',
    'scripts/smoke_test.py',
    'README.md',
    'enhanced_chroma_analyzer.py',
    'wsgi_production.py',
    'app_https.py',
    'librosa_chroma_analyzer.py',
]

for f in files:
    if os.path.exists(f):
        h = hashlib.sha256()
        with open(f, 'rb') as fh:
            while True:
                chunk = fh.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        print(f + ' ' + h.hexdigest())
    else:
        print(f + ' MISSING')
