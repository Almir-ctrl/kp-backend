import subprocess
import sys
import os


def test_wsgi_import_with_eventlet():
    """Spawn a subprocess that imports wsgi_production with eventlet available.

    The subprocess should exit 0 and print OK if import succeeded.
    """
    env = os.environ.copy()
    # Ensure python can import eventlet in subprocess; test runner will install it.
    cmd = [sys.executable, "-c", 'import wsgi_production; print("OK")']
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print("STDOUT:", p.stdout)
    print("STDERR:", p.stderr)
    assert p.returncode == 0
    assert "OK" in p.stdout
    assert p.returncode == 0

    assert "OK" in p.stdout
