# Karaoke Feature Guide

## Overview

The AI Music Separator backend now includes automatic karaoke generation that creates synced lyric files and embeds metadata into audio tracks. This feature integrates seamlessly with the existing Demucs separation and Gemma 3n transcription pipeline.

## Features

- **Automatic Karaoke Generation**: Triggered automatically after successful audio separation and transcription
- **LRC Format**: Industry-standard synchronized lyrics format with timestamps
- **Metadata Embedding**: Lyrics embedded directly into MP3 ID3 tags
- **Dedicated Storage**: All karaoke files saved to `outputs/Karaoke-pjesme/{file_id}/`
- **Complete Package**: Includes instrumental track, LRC file, and sync metadata JSON

## How It Works

### 1. Upload & Auto-Processing

When you upload an audio file with `auto_process=true` (default):

```bash
POST /upload?model=demucs
Content-Type: multipart/form-data
file: <your_audio_file.mp3>
auto_process: true
```

The backend automatically:
1. **Separates** audio with Demucs (2-stem: vocals + instrumental)
2. **Transcribes** lyrics with Gemma 3n in parallel
3. **Generates** karaoke package with synced lyrics

### 2. Karaoke Processing Flow

```
Upload → Demucs Separation → Gemma 3n Transcription → Karaoke Generation
           (vocals.mp3)        (lyrics text)            (synced LRC)
           (no_vocals.mp3)                              (embedded metadata)
```

### 3. Output Structure

For a file with ID `abc123`, the karaoke output includes:

```
outputs/Karaoke-pjesme/abc123/
├── abc123_karaoke.mp3      # Instrumental with embedded lyrics
├── abc123_karaoke.lrc      # Synced lyrics in LRC format
└── abc123_sync.json        # Complete sync metadata
```

## API Response

### Enhanced Upload Response

```json
{
  "file_id": "abc123",
  "filename": "song.mp3",
  "status": "completed",
  "tracks": [
    {
      "name": "vocals",
      "download_url": "/download/abc123/vocals"
    },
    {
      "name": "no_vocals",
      "download_url": "/download/abc123/no_vocals"
    }
  ],
  "transcription": {
    "status": "completed",
    "text": "Full transcribed lyrics...",
    "model": "gemma-3n",
    "download_url": "/download/abc123/transcription.txt"
  },
  "karaoke": {
    "status": "completed",
    "karaoke_dir": "outputs/Karaoke-pjesme/abc123",
    "lrc_file": "outputs/Karaoke-pjesme/abc123/abc123_karaoke.lrc",
    "audio_file": "outputs/Karaoke-pjesme/abc123/abc123_karaoke.mp3",
    "total_lines": 42,
    "duration": 180.5,
    "download_url": "/download/abc123/abc123_karaoke.mp3"
  }
}
```

## File Formats

### LRC Format (Synced Lyrics)

```lrc
[ti:Karaoke Song]
[ar:Unknown Artist]
[al:]
[length:03:00]

[00:00.50]First line of lyrics
[00:05.20]Second line of lyrics
[00:10.80]Third line continues here
[00:15.40]And so on with timestamps
```

- Each line prefixed with `[MM:SS.CC]` timestamp
- Standard karaoke player compatible
- UTF-8 encoding supports all languages

### Sync Metadata JSON

```json
{
  "file_id": "abc123",
  "duration": 180.5,
  "total_lines": 42,
  "synced_lyrics": [
    {
      "timestamp": 0.5,
      "lrc_format": "[00:00.50]",
      "text": "First line of lyrics"
    },
    {
      "timestamp": 5.2,
      "lrc_format": "[00:05.20]",
      "text": "Second line of lyrics"
    }
  ],
  "lrc_file": "abc123_karaoke.lrc",
  "audio_file": "abc123_karaoke.mp3",
  "generated_at": "2025-01-14T12:30:45.123456"
}
```

### ID3 Metadata Embedding

The karaoke MP3 includes embedded ID3v2 tags:

- **USLT** (Unsynchronized Lyrics): Full lyrics text
- **TIT2** (Title): "Karaoke - {file_id}"
- **TPE1** (Artist): "AI Music Separator"
- **TALB** (Album): "Karaoke Collection"

## Download Endpoints

### Download Karaoke Audio

```bash
GET /download/{file_id}/{file_id}_karaoke.mp3
```

Returns the instrumental track with embedded lyrics metadata.

### Download LRC File

```bash
GET /download/{file_id}/{file_id}_karaoke.lrc
```

Returns the synchronized lyrics file.

### Download All Tracks

```bash
GET /download/{file_id}
```

Returns all available files including karaoke outputs.

## Using the Karaoke Files

### With Media Players

**VLC Media Player:**
1. Open the karaoke MP3 file
2. Place the LRC file in the same directory
3. Lyrics will display automatically

**Windows Media Player:**
- Reads embedded ID3 USLT tag
- Displays full lyrics (non-synced)

**Karaoke Software:**
- Import LRC file directly
- Most karaoke apps support standard LRC format

### Programmatic Access

**Python Example:**

```python
import requests
import json

# Upload and get karaoke
with open('song.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/upload?model=demucs',
        files={'file': f},
        data={'auto_process': 'true'}
    )

result = response.json()

if result.get('karaoke', {}).get('status') == 'completed':
    # Download karaoke audio
    karaoke_url = f"http://localhost:5000{result['karaoke']['download_url']}"
    audio_response = requests.get(karaoke_url)
    
    with open('karaoke.mp3', 'wb') as f:
        f.write(audio_response.content)
    
    # Parse sync metadata
    with open(result['karaoke']['sync_metadata'], 'r') as f:
        metadata = json.load(f)
    
    print(f"Generated {metadata['total_lines']} synced lyrics")
    print(f"Duration: {metadata['duration']} seconds")
```

## Configuration

### Lyrics Sync Algorithm

Current implementation uses **uniform distribution** for timestamp generation:

```python
time_per_line = total_duration / number_of_lines
```

For production use, consider:
- **Gemma 3n Enhanced**: Use AI model for word-level timing
- **Forced Alignment**: Tools like Gentle or Montreal Forced Aligner
- **Manual Editing**: Post-process LRC files for precise timing

### Customization Options

Edit `models.py` `KaraokeProcessor` class:

```python
# Custom LRC metadata
f.write("[ti:Your Custom Title]\n")
f.write("[ar:Artist Name]\n")
f.write("[al:Album Name]\n")

# Adjust time distribution
time_per_line = duration / len(lines)
pause_between_lines = 0.5  # Add pauses
timestamp = i * time_per_line + pause_between_lines
```

## Testing

Run the test script to verify karaoke generation:

```powershell
python test_karaoke.py
```

This will:
1. Find a test audio file in `uploads/`
2. Run Demucs separation if needed
3. Run Gemma 3n transcription if needed
4. Generate complete karaoke package
5. Display LRC preview and metadata

## Troubleshooting

### Common Issues

**1. Karaoke Not Generated**

Check upload response for errors:
```json
{
  "karaoke": {
    "status": "failed",
    "error": "reason here"
  }
}
```

Solutions:
- Ensure Demucs separation succeeded
- Verify transcription completed
- Check `outputs/Karaoke-pjesme/` permissions

**2. No Lyrics in Audio File**

- Metadata embedding failed (check logs)
- Use LRC file as fallback
- Player might not support USLT tag

**3. Timing Misalignment**

Current algorithm uses uniform distribution:
- Short lines appear too fast
- Long lines might lag

Solutions:
- Manually edit LRC file timestamps
- Implement advanced sync algorithm
- Use forced alignment tools

### Debug Mode

Enable detailed logging:

```python
# In app.py, before karaoke generation
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check karaoke processor logs:
```
Auto-generating karaoke for abc123
Karaoke generation completed: {...}
```

## Performance

- **Karaoke Generation Time**: ~1-3 seconds (after separation/transcription)
- **File Size**: Same as instrumental track + ~2KB for metadata
- **CPU Usage**: Minimal (mostly I/O operations)

## Future Enhancements

### Planned Features

1. **Word-Level Timing**: Use Gemma 3n for precise word timestamps
2. **Multi-Language Support**: Detect language and adjust LRC metadata
3. **Background Vocals**: Option to include or exclude backing vocals
4. **Pitch Shifting**: Adjust key for different vocal ranges
5. **Video Integration**: Generate karaoke video with lyrics overlay

### API Extensions

```python
# Future endpoint
POST /process/karaoke/<file_id>
{
  "include_backing_vocals": true,
  "pitch_shift_semitones": -2,
  "sync_algorithm": "forced_alignment",
  "output_format": "lrc+srt+vtt"
}
```

## Integration with Lion's Roar Studio

### React Example

```jsx
function KaraokePlayer({ fileId }) {
  const [karaoke, setKaraoke] = useState(null);
  
  useEffect(() => {
    // Fetch karaoke metadata
    fetch(`http://localhost:5000/status/${fileId}`)
      .then(res => res.json())
      .then(data => setKaraoke(data.karaoke));
  }, [fileId]);
  
  if (!karaoke) return <div>Loading karaoke...</div>;
  
  return (
    <div>
      <h2>Karaoke Player</h2>
      <audio controls src={karaoke.download_url} />
      <div className="lyrics">
        {karaoke.synced_lyrics.map((line, i) => (
          <p key={i} data-time={line.timestamp}>
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}
```

## Resources

- **LRC Format Spec**: https://en.wikipedia.org/wiki/LRC_(file_format)
- **Mutagen Docs**: https://mutagen.readthedocs.io/
- **Demucs Project**: https://github.com/facebookresearch/demucs
- **Gemma Models**: https://ai.google.dev/gemma

## Support

For issues or feature requests related to karaoke generation:
1. Check this guide first
2. Review server logs in `logs/app.log`
3. Run `test_karaoke.py` to isolate issues
4. Open an issue with:
   - Upload response JSON
   - Error messages from logs
   - Sample audio characteristics

---

**Last Updated**: 2025-01-14  
**Version**: 1.0.0  
**Author**: AI Music Separator Team
