# Karaoke API Endpoints

## Overview
Two new Flask endpoints have been added to serve karaoke files and list available karaoke songs.

---

## Endpoints

### 1. **GET /songs**
Lists all uploaded songs with karaoke availability status.

**Response:**
```json
{
  "songs": [
    {
      "filename": "song.wav",
      "file_id": "0e9ae407-1377-42d5-bc31-e455ee2c84e4",
      "size_bytes": 29475028,
      "has_karaoke": true,
      "karaoke_url": "/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4"
    }
  ],
  "count": 10
}
```

**Example:**
```bash
curl http://localhost:5000/songs
```

---

### 2. **GET /karaoke/songs**
Lists all available karaoke songs with detailed metadata.

**Response:**
```json
{
  "songs": [
    {
      "file_id": "0e9ae407-1377-42d5-bc31-e455ee2c84e4",
      "karaoke_dir": "/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4",
      "duration": 167.13,
      "total_lines": 11,
      "generated_at": "2025-10-19 09:36:25.660729",
      "files": {
        "lrc": "/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_karaoke.lrc",
        "audio": "/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_karaoke.mp3",
        "metadata": "/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_sync.json"
      }
    }
  ],
  "count": 2
}
```

**Example:**
```bash
curl http://localhost:5000/karaoke/songs
```

---

### 3. **GET /karaoke/<file_id>/<filename>**
Serves individual karaoke files (audio, LRC, or metadata JSON).

**Parameters:**
- `file_id`: The unique identifier of the song
- `filename`: The specific file to download

**Supported file types:**
- `.mp3` - Karaoke audio with embedded metadata (mimetype: `audio/mpeg`)
- `.lrc` - Synced lyrics in LRC format (mimetype: `text/plain`)
- `.json` - Sync metadata with timestamps (mimetype: `application/json`)

**Examples:**
```bash
# Get LRC lyrics
curl http://localhost:5000/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_karaoke.lrc

# Get karaoke audio
curl http://localhost:5000/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_karaoke.mp3 -o song.mp3

# Get sync metadata
curl http://localhost:5000/karaoke/0e9ae407-1377-42d5-bc31-e455ee2c84e4/0e9ae407-1377-42d5-bc31-e455ee2c84e4_sync.json
```

---

## File Structure

Karaoke files are stored in:
```
outputs/
  Karaoke-pjesme/
    <file_id>/
      <file_id>_karaoke.mp3      # Instrumental with embedded lyrics
      <file_id>_karaoke.lrc      # Synced lyrics (LRC format)
      <file_id>_sync.json        # Full metadata with timestamps
```

---

## Integration Example

### Lion's Roar Studio Player Integration
```javascript
// Fetch karaoke songs list
fetch('http://localhost:5000/karaoke/songs')
  .then(res => res.json())
  .then(data => {
    data.songs.forEach(song => {
      console.log(`Song: ${song.file_id}`);
      console.log(`Audio: ${song.files.audio}`);
      console.log(`Lyrics: ${song.files.lrc}`);
      console.log(`Duration: ${song.duration}s`);
    });
  });

// Load a specific karaoke file
const fileId = '0e9ae407-1377-42d5-bc31-e455ee2c84e4';
const audioUrl = `http://localhost:5000/karaoke/${fileId}/${fileId}_karaoke.mp3`;
const lrcUrl = `http://localhost:5000/karaoke/${fileId}/${fileId}_karaoke.lrc`;

// Use in HTML5 audio player
const audio = new Audio(audioUrl);
audio.play();

// Fetch and parse LRC
fetch(lrcUrl)
  .then(res => res.text())
  .then(lrc => {
    // Parse LRC format and sync with audio playback
    console.log('LRC content:', lrc);
  });
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Description of the error"
}
```

**Common HTTP status codes:**
- `200` - Success
- `404` - File or karaoke not found
- `500` - Server error

---

## Notes

1. **Karaoke Generation**: Karaoke files are automatically generated when a file is uploaded with `auto_process=true` and both separation and transcription succeed.

2. **File Naming**: All karaoke files use the format `<file_id>_karaoke.<ext>` for consistency.

3. **CORS**: The server supports CORS, so these endpoints can be accessed from web frontends on different domains.

4. **Performance**: Large karaoke files are streamed efficiently using Flask's `send_file` function.

---

## Testing

Run the included tests:
```bash
# Test /songs endpoint
curl http://localhost:5000/songs | jq

# Test /karaoke/songs endpoint
curl http://localhost:5000/karaoke/songs | jq

# Test file serving
curl http://localhost:5000/karaoke/<file_id>/<filename>
```
