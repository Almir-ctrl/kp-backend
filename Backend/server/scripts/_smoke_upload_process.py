import requests
from pathlib import Path

backend = 'http://127.0.0.1:5000'
filep = Path('uploads') / (
    "Aca Lukas - Kuda idu ljudi kao ja - (Audio 1995).mp3"
)

print('Uploading', filep)
with filep.open('rb') as fh:
    r = requests.post(
        backend + '/upload/whisper',
        files={'file': (filep.name, fh)},
        timeout=300,
    )
    print('upload status', r.status_code)
    try:
        print(r.text)
        j = r.json()
    except Exception as e:
        print('upload response not json', e)
        raise
    fid = j.get('file_id')
    if fid:
        print('Processing', fid)
        pr = requests.post(
            backend + f'/process/whisper/{fid}', timeout=600
        )
        print('process status', pr.status_code)
        try:
            print(pr.json())
        except Exception:
            print(pr.text)
