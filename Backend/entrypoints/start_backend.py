"""
Simple script to start backend server from any directory
"""
import os
import sys
import subprocess
import time

# Change to backend directory
backend_dir = r"C:\Users\almir\AiMusicSeparator-Backend"
os.chdir(backend_dir)

print(f"Changed directory to: {os.getcwd()}")
print("Starting FULL backend server (app.py with all endpoints)...")

# Start server as detached background process
process = subprocess.Popen(
    [sys.executable, "app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
)

print(f"✅ Server started with PID: {process.pid}")
print("Server is running in a new console window.")
print("To stop the server, close the console window or use Task Manager.")
time.sleep(2)  # Wait a bit to let server start

# Print first few lines of output
try:
    for _ in range(10):
        line = process.stdout.readline()
        if line:
            print(line.strip())
        else:
            break
except Exception:
    # If the process pipes are closed or unavailable, ignore and continue
    pass

print("\n✅ Server should be ready now at http://127.0.0.1:5000")
