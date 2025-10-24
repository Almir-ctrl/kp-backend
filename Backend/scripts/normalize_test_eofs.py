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
        with open(f, 'r', encoding='utf-8') as fh:
            lines = fh.read().splitlines()
        # remove trailing blank lines
        while lines and lines[-1].strip() == '':
            lines.pop()
        new = '\n'.join(lines) + '\n'
        with open(f, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(new)
        print('normalized', f)
    except Exception as e:
        print('error', f, e)
