from huggingface_hub import snapshot_download
import os

MODEL_NAME = "openai/whisper-large-v3"
OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'models', 'whisper', MODEL_NAME.replace('/', '_')))

os.makedirs(OUT_DIR, exist_ok=True)
print(f"Downloading repository {MODEL_NAME} into {OUT_DIR} using huggingface_hub.snapshot_download...")
# snapshot_download will download model files into a cache directory by default; local_dir writes into OUT_DIR
snapshot_download(repo_id=MODEL_NAME, local_dir=OUT_DIR, local_dir_use_symlinks=False)
print("Download finished.")
