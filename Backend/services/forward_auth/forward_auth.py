from fastapi import FastAPI, Request
import os
import jwt

app = FastAPI()
JWT_SECRET = os.environ.get('JWT_SECRET', 'changeme')


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/verify')
async def verify(request: Request):
    # nginx will forward Authorization header (Bearer <token>)
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        from fastapi import Response
        return Response(status_code=401, content='Missing token')
    token = auth.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.PyJWTError:
        from fastapi import Response
        return Response(status_code=401, content='Invalid token')
    # Optionally set headers for upstream apps
    from fastapi.responses import JSONResponse
    return JSONResponse({'valid': True, 'sub': payload.get('sub')})
