import os

# Ensure CI_SMOKE mode
os.environ['CI_SMOKE'] = 'true'

import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import WhisperManager

wm = WhisperManager()
from app import app

with app.app_context():
	res = wm.transcribe(
		'ci-test', str(ROOT / 'tests' / 'fixtures' / 'sample.wav'), 'base'
	)
	print('CI Whisper transcribe result:', res)
