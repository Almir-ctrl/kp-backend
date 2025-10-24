"""Test full processing pipeline"""
import sys
import os
import codecs

# Set UTF-8 output
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set Flask app context
os.environ['FLASK_APP'] = 'app.py'

from pathlib import Path
from models import get_processor


def test_pipeline():
    """Test the full processing pipeline"""

    # Find a recent upload
    upload_dir = Path("uploads")
    uploads = list(upload_dir.glob("*.wav"))

    if not uploads:
        print("No uploads found!")
        return

    test_file = uploads[-1]  # Most recent
    file_id = test_file.stem

    print(f"\n{'='*60}")
    print(f"Testing pipeline with: {test_file.name}")
    print(f"File ID: {file_id}")
    print(f"{'='*60}\n")

    # Test Demucs
    print("1. Testing Demucs separation...")
    try:
        demucs = get_processor('demucs')
        result = demucs.process(file_id, test_file, model_variant='htdemucs')
        print(f"   ✓ Demucs SUCCESS: {result}")
    except Exception as e:
        print(f"   ✗ Demucs FAILED: {e}")
        return

    # Test Gemma 3n
    print("\n2. Testing Gemma 3n transcription...")
    try:
        gemma = get_processor('gemma_3n')
        result = gemma.process(file_id, test_file, model_variant='gemma-2-2b', task='transcribe')
        print("   ✓ Gemma SUCCESS")
        out_files = "{}, {}".format(
            result.get('output_json_file'),
            result.get('output_text_file'),
        )
        print("   Output files: {}".format(out_files))
    except Exception as e:
        print(f"   ✗ Gemma FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test Karaoke
    print("\n3. Testing Karaoke generation...")
    try:
        from models import KaraokeProcessor

        # Find instrumental and vocals
        demucs_output = Path(f"outputs/htdemucs/{file_id}")
        instrumental = demucs_output / "no_vocals.mp3"
        vocals = demucs_output / "vocals.mp3"

        if not instrumental.exists():
            print(f"   ✗ Instrumental not found: {instrumental}")
            return

        karaoke = KaraokeProcessor()
        transcription_text = result.get('analysis_summary', '')

        karaoke_result = karaoke.process(
            file_id,
            str(instrumental),
            str(vocals) if vocals.exists() else str(test_file),
            transcription_text,
            original_audio_path=str(test_file)
        )
        print(f"   ✓ Karaoke SUCCESS: {karaoke_result}")
    except Exception as e:
        print(f"   ✗ Karaoke FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n{'='*60}")
    print("✓ FULL PIPELINE SUCCESS!")
    print("{}\n".format('=' * 60))


if __name__ == '__main__':
    # Create Flask app context
    from app import app

    with app.app_context():
        test_pipeline()
