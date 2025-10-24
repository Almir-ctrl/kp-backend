#!/usr/bin/env python3
"""
Regenerate karaoke for an existing song with proper lyrics and metadata
"""
import os
import sys
# pathlib.Path not required here; keep imports minimal

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import KaraokeProcessor


def regenerate_karaoke(file_id):
    """Regenerate karaoke package for a song"""

    # Paths
    output_dir = os.path.join('outputs', file_id)

    if not os.path.exists(output_dir):
        print(f"❌ Error: Output directory not found: {output_dir}")
        return False

    # Find files
    instrumental_file = None
    vocals_file = None
    transcription_file = None
    metadata_file = os.path.join(output_dir, 'metadata.json')

    # Look for Demucs output (htdemucs folder)
    htdemucs_dir = os.path.join(output_dir, 'htdemucs')
    if os.path.exists(htdemucs_dir):
        for subdir in os.listdir(htdemucs_dir):
            subdir_path = os.path.join(htdemucs_dir, subdir)
            if os.path.isdir(subdir_path):
                for f in os.listdir(subdir_path):
                    if 'no_vocals' in f.lower():
                        instrumental_file = os.path.join(subdir_path, f)
                    elif 'vocals' in f.lower() and 'no_vocals' not in f.lower():
                        vocals_file = os.path.join(subdir_path, f)

    # Find transcription file (try all variants)
    for variant in ['large', 'medium', 'base', 'small']:
        txt_file = os.path.join(output_dir, f'transcription_{variant}.txt')
        if os.path.exists(txt_file):
            transcription_file = txt_file
            break

    # Load metadata
    artist = 'Unknown Artist'
    song_name = 'Unknown Title'
    if os.path.exists(metadata_file):
        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            artist = metadata.get('artist', artist)
            song_name = metadata.get('title', song_name)

    # Check requirements
    if not instrumental_file:
        print("❌ Error: Instrumental file not found")
        print(f"   Searched in: {htdemucs_dir}")
        return False

    if not transcription_file:
        print("❌ Error: Transcription file not found")
        print(f"   Searched in: {output_dir}")
        return False

    # Read transcription
    with open(transcription_file, 'r', encoding='utf-8') as f:
        transcription_text = f.read()

    if not transcription_text.strip():
        print("❌ Error: Transcription file is empty")
        return False

    # Get upload path (for timing analysis)
    upload_file = os.path.join('uploads', f'{file_id}.mp3')
    if not os.path.exists(upload_file):
        # Try other extensions
        for ext in ['.wav', '.ogg', '.flac', '.m4a']:
            alt_upload = os.path.join('uploads', f'{file_id}{ext}')
            if os.path.exists(alt_upload):
                upload_file = alt_upload
                break

    print("📋 Files found:")
    print(f"  - Instrumental: {os.path.basename(instrumental_file)}")
    print(f"  - Vocals: {os.path.basename(vocals_file) if vocals_file else 'N/A'}")
    print(f"  - Transcription: {os.path.basename(transcription_file)}")
    print(f"  - Original: {os.path.basename(upload_file)}")
    print(f"  - Artist: {artist}")
    print(f"  - Song: {song_name}")
    print(f"  - Transcription length: {len(transcription_text)} chars")
    print()

    # Create karaoke processor
    print("🎤 Generating karaoke...")
    processor = KaraokeProcessor()

    try:
        result = processor.process(
            file_id=file_id,
            instrumental_path=instrumental_file,
            vocals_path=vocals_file or upload_file,
            transcription_text=transcription_text,
            original_audio_path=upload_file,
            artist=artist,
            song_name=song_name
        )

        print("✅ Karaoke generated successfully!")
        print(f"  - Directory: {result['karaoke_dir']}")
        print(f"  - LRC file: {os.path.basename(result['lrc_file'])}")
        print(f"  - Audio: {os.path.basename(result['audio_with_metadata'])}")
        print(f"  - Total lines: {result['total_lines']}")
        print(f"  - Duration: {result['duration']:.2f}s")

        return True

    except Exception as e:
        print(f"❌ Error generating karaoke: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python regenerate_karaoke.py <file_id>")
        print()
        print("Example:")
        print("  python regenerate_karaoke.py 24d60dc7-a348-4047-ac73-e1326bc25275")
        sys.exit(1)

    file_id = sys.argv[1]
    success = regenerate_karaoke(file_id)

    sys.exit(0 if success else 1)
