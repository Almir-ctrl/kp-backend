from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
import os
import uuid
import shutil

app = FastAPI()
OUTPUT_BASE = os.environ.get('OUTPUT_BASE','/outputs')
API_KEY = os.environ.get('API_KEY','changeme')

@app.get('/health')
async def health():
    return {'status':'ok'}

@app.post('/jobs')
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    upload_dir = os.path.join('/uploads', file_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    job_id = str(uuid.uuid4())
    out_dir = os.path.join(OUTPUT_BASE, file_id, 'demucs')
    os.makedirs(out_dir, exist_ok=True)

    # For prototype, just copy the file to outputs as "vocals.mp3" and "no_vocals.mp3"
    def work():
        shutil.copy(file_path, os.path.join(out_dir, 'vocals.mp3'))
        shutil.copy(file_path, os.path.join(out_dir, 'no_vocals.mp3'))
        # Optionally call orchestrator callback
        callback = os.environ.get('ORCHESTRATOR_CALLBACK')
        if callback:
            try:
                import requests
                requests.post(callback, json={'job_id': job_id, 'file_id': file_id, 'outputs': ['vocals.mp3','no_vocals.mp3']})
            except Exception:
                pass

    background_tasks.add_task(work)
    return {'job_id': job_id, 'file_id': file_id, 'status': 'processing'}
