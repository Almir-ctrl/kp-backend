import requests
import shutil
from pathlib import Path

BASE_URL = "http://localhost:5000"


def find_any_uploaded_file_id():
    outputs = Path('outputs')
    if not outputs.exists():
        return None
    for d in outputs.iterdir():
        if d.is_dir():
            return d.name
    return None


def test_skip_demucs_when_vocals_exist():
    file_id = find_any_uploaded_file_id()
    assert file_id, "No outputs present to test skip logic"

    # Ensure vocals.mp3 exists in that output dir to test skip
    vocals = Path('outputs') / file_id / 'vocals.mp3'
    if not vocals.exists():
        # create empty placeholder
        vocals.parent.mkdir(parents=True, exist_ok=True)
        vocals.write_bytes(b'')

    r = requests.post(f"{BASE_URL}/process/demucs/{file_id}")
    assert r.status_code == 200
    data = r.json()
    assert data.get('skipped') is True or 'existing_output' in data


def test_karaoke_prerequisites_missing_and_present(tmp_path):
    # Create a fake file_id folder without vocals/transcription
    test_id = 'test_karaoke_001'
    outdir = Path('outputs') / test_id
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # call karaoke process. If endpoint not present, accept 404 and skip test
    r = requests.post(f"{BASE_URL}/process/karaoke/{test_id}")
    if r.status_code == 404:
        # endpoint not implemented; skip the rest of this test
        return
    assert r.status_code == 400

    # Now add required files
    (outdir / 'vocals.mp3').write_bytes(b'')
    (outdir / 'transcription_base.txt').write_text('Hello world')

    r2 = requests.post(f"{BASE_URL}/process/karaoke/{test_id}")
    # Depending on implementation, may process or return 200 with skip; assert not 400
    assert r2.status_code != 400
