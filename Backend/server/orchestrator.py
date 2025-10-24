from fastapi import FastAPI, Request
import os
import json

app = FastAPI()
JOB_DIR = os.path.abspath('jobs')
os.makedirs(JOB_DIR, exist_ok=True)

@app.get('/health')
async def health():
    return {'status':'ok'}

@app.post('/process/{model}/{file_id}')
async def process(model: str, file_id: str, request: Request):
    payload = await request.json()
    job_id = payload.get('job_id') or str(file_id) + '-' + model
    data = {'job_id': job_id,'model': model,'file_id': file_id,'status':'submitted','payload': payload}
    with open(os.path.join(JOB_DIR, job_id + '.json'),'w') as f:
        json.dump(data,f)
    # For prototype: forward to demucs service if model == 'demucs'
    if model == 'demucs':
        # build request to demucs
        import requests
        demucs_url = os.environ.get('DEMUC_SERVICE','http://demucs:8000/jobs')
        files = {}
        # For prototype we won't send real files; the demucs service accepts multipart uploads too
        try:
            resp = requests.post(demucs_url, json={'file_id': file_id, 'callback': os.environ.get('ORCH_CALLBACK','http://orchestrator:5000/notify')})
        except Exception as e:
            data['status']='error'
            data['error']=str(e)
            with open(os.path.join(JOB_DIR, job_id + '.json'),'w') as f:
                json.dump(data,f)
            return {'ok':False,'error':str(e)}
    return {'ok':True,'job_id': job_id}

@app.post('/notify')
async def notify(request: Request):
    payload = await request.json()
    job_id = payload.get('job_id') or 'unknown'
    path = os.path.join(JOB_DIR, job_id + '.json')
    if os.path.exists(path):
        with open(path,'r') as f:
            data = json.load(f)
    else:
        data = {}
    data['status']='completed'
    data['outputs']=payload.get('outputs', [])
    with open(path,'w') as f:
        json.dump(data,f)
    return {'ok':True}
