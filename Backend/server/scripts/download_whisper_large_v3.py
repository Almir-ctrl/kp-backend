import os
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

MODEL_NAME = "openai/whisper-large-v3"
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'models', 'whisper', MODEL_NAME.replace('/', '_'))

os.makedirs(OUT_DIR, exist_ok=True)
print(f"Downloading processor and model {MODEL_NAME} into {OUT_DIR}...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)
processor.save_pretrained(OUT_DIR)
model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_NAME)
model.save_pretrained(OUT_DIR)
print("Done.")
