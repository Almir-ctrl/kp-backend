# Quick Reference: Flask Hooks

**For developers working on AiMusicSeparator Backend**

## TL;DR - Adding Hooks to Any Flask App

```python
from flask import Flask
from server.logging_utils import setup_flask_app_hooks

app = Flask(__name__)
# ... your config ...

# ONE LINE TO ADD EVERYTHING:
setup_flask_app_hooks(app, log_dir='logs')

# That's it! You now have:
# ✅ Request ID tracking
# ✅ Error handlers (JSON errors)
# ✅ Logging with rotation
# ✅ CORS headers
```

---

## Request ID Pattern

### Backend automatically:
- Accepts `X-Request-ID` header from client
- Generates UUID if not provided
- Returns `X-Request-ID` in response
- Logs all actions with request ID
- Includes in error responses

### Lion's Roar Studio example (JavaScript):
```javascript
const reqId = crypto.randomUUID();
const response = await fetch('/api/endpoint', {
  headers: { 'X-Request-ID': reqId }
});
const responseId = response.headers.get('X-Request-ID');
// Use responseId for logging and error reporting
```

---

## Error Response Format

All errors return JSON:

```json
{
  "error": "Error message",
  "code": 404,
  "request_id": "uuid-here",
  "path": "/requested/path"  // 404 only
}
```

Debug mode adds `exception` and `traceback` fields.

---

## Logging

**Text logs:** `logs/app.log`  
**JSON logs:** `logs/app.json.log`

Both rotate at 5MB (keeps last 5 files).

Log format includes request ID:
```
2025-10-19 10:30:45 [INFO] [uuid] Request: GET /health from 127.0.0.1
```

---

## Testing Hooks

```bash
# Run hook tests
pytest tests/test_hooks.py -v

# Run WebSocket app integration tests
pytest tests/test_websocket_hooks.py -v
```

---

## Files to Know

- **`server/logging_utils.py`** - Shared utilities (use this!)
- **`tests/test_hooks.py`** - Test examples
- **`HOOK_IMPLEMENTATION_SUMMARY.md`** - Full documentation
- **`HOOKS_ANALYSIS.md`** - Analysis and design decisions

---

## Common Tasks

### Add logging to new Flask app:
```python
from server.logging_utils import setup_flask_app_hooks
setup_flask_app_hooks(app, log_dir='logs')
```

### Get request ID in route handler:
```python
from flask import request

@app.route('/my-route')
def my_route():
    req_id = request.request_id
    app.logger.info("Processing request", extra={"request_id": req_id})
    return jsonify({"request_id": req_id})
```

### Log with request context:
```python
app.logger.info("Message", extra={"request_id": request.request_id})
app.logger.error("Error occurred", extra={"request_id": request.request_id})
```

### Return error with request ID:
```python
from flask import jsonify, request

req_id = getattr(request, 'request_id', None)
return jsonify({"error": "Something went wrong", "request_id": req_id}), 500
```

---

## Debugging

### Search logs by request ID:
```bash
# Text logs
grep "uuid-here" logs/app.log

# JSON logs (jq required)
jq 'select(.request_id=="uuid-here")' logs/app.json.log
```

### Correlate frontend and backend:
1. Lion's Roar Studio sends request with `X-Request-ID`
2. Backend logs all operations with that ID
3. Backend returns same ID in response
4. Search logs on both sides for the UUID

---

## Apps Using Hooks

- ✅ **app.py** - Main app with full implementation
- ✅ **app_websocket.py** - Uses shared utilities
- ✅ **app_https.py** - Inherits from app.py
- ✅ **production.py** - Inherits from app.py
- ⏭️ **app_simple.py** - Intentionally minimal (no hooks)
- ⏭️ **server/backend_skeleton.py** - Can be updated (optional)

---

## Test Coverage

**34 tests, 100% passing:**
- Request ID generation and tracking
- Error handler JSON formatting
- CORS header management
- Request ID in errors
- Logging integration
- Modular usage
- Schema validation
- Concurrency handling

---

## Need Help?

1. Read `HOOK_IMPLEMENTATION_SUMMARY.md` for details
2. Check `tests/test_hooks.py` for examples
3. Look at `app_websocket.py` for usage example
4. Ask in team chat with request ID for debugging

---

**Last Updated:** October 19, 2025  
**Status:** Production Ready ✅
