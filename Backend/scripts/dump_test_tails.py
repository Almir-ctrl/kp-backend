files = [
    'tests/test_gpu_status.py',
    'tests/test_hooks.py',
    'tests/test_integration.py',
    'tests/test_resumable.py',
    'tests/test_skip_and_karaoke.py',
    'tests/test_upload_duplicate.py',
    'tests/test_websocket_hooks.py',
    'tests/test_whisper_manager.py',
]

for f in files:
    try:
        with open(f, 'rb') as fh:
            data = fh.read()
        print('---', f, '---')
        # show last 120 bytes and repr
        tail = data[-120:]
        print(repr(tail))
    except Exception as e:
        print('ERR', f, e)
