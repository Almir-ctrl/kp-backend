import io
import time
import pytest
from server.backend_skeleton import app, init_db


@pytest.fixture(scope="module")
def client():
    init_db()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_upload_process_download(client):
    # create a small fake audio file
    fake_wav = io.BytesIO(b"RIFF....WAVEfmt ")
    fake_wav.name = "sample.wav"

    data = {"file": (fake_wav, "sample.wav")}
    rv = client.post("/upload", data=data, content_type="multipart/form-data")
    assert rv.status_code in (200, 201)
    body = rv.get_json()
    file_id = body["file_id"]

    # start processing
    rv = client.post(f"/process/demucs/{file_id}", json={})
    assert rv.status_code == 202
    job = rv.get_json()
    job_id = job["job_id"]

    # poll status until complete (with timeout)
    deadline = time.time() + 10
    status = None
    while time.time() < deadline:
        rv = client.get(f"/status/{job_id}")
        assert rv.status_code == 200
        status = rv.get_json()
        if status.get("status") == "completed":
            break
        time.sleep(0.5)

    assert status is not None
    assert status.get("status") == "completed"

    # download artifact
    rv = client.get(f"/download/{file_id}/instrumental")
    assert rv.status_code == 200
    assert rv.data is not None
