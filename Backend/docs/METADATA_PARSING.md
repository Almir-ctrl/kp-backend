# Artist & Song Name Parsing Feature

## Overview
The backend now automatically extracts artist and song names from uploaded filenames during the separation process.

## Filename Format

### Expected Format:
```
Artist - Song Name.ext
```

### Examples:
```
Taylor Swift - Anti-Hero.mp3           → Artist: "Taylor Swift", Song: "Anti-Hero"
The Beatles - Hey Jude (Remastered).wav → Artist: "The Beatles", Song: "Hey Jude"
Adele-Hello [Official].flac            → Artist: "Adele", Song: "Hello"
```

### Parsing Rules:

1. **Splits on dash** (`-` or ` - `)
   - Before dash = Artist
   - After dash = Song Name

2. **Removes brackets and content**:
   - `(...)` - Parentheses removed
   - `[...]` - Square brackets removed
   - `{...}` - Curly braces removed

3. **Cleans whitespace**:
   - Multiple spaces → single space
   - Leading/trailing spaces removed

4. **Fallback behavior**:
   - No dash found → Artist: "Unknown Artist", Song: filename
   - Empty artist → "Unknown Artist"
   - Empty song → "Untitled"

## Implementation

### Parsing Function
```python
def parse_artist_song(filename):
    """Parse artist and song name from filename."""
    import re
    
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    # Remove brackets: (text), [text], {text}
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = re.sub(r'\{[^}]*\}', '', name)
    
    # Clean whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Split by dash
    if ' - ' in name:
        artist, song = name.split(' - ', 1)
    elif '-' in name:
        artist, song = name.split('-', 1)
    else:
        artist, song = 'Unknown Artist', name
    
    return {
        'artist': artist.strip() or 'Unknown Artist',
        'song': song.strip() or 'Untitled'
    }
```

## Metadata Storage

### Upload Metadata File
Saved as: `uploads/<file_id>_metadata.json`

```json
{
  "file_id": "43485f0b-7144-4081-974c-24d77efbe117",
  "original_filename": "Adele - Hello (Official).mp3",
  "artist": "Adele",
  "song": "Hello",
  "upload_time": "2025-10-19T10:30:45.123456",
  "file_extension": "mp3"
}
```

### Separation Metadata File
Saved as: `outputs/htdemucs/<file_id>/separation_metadata.json`

```json
{
  "file_id": "43485f0b-7144-4081-974c-24d77efbe117",
  "artist": "Adele",
  "song": "Hello",
  "original_filename": "Adele - Hello (Official).mp3",
  "separation_time": "2025-10-19T10:31:15.789012",
  "model": "demucs",
  "model_variant": "htdemucs",
  "tracks": ["vocals", "no_vocals"]
}
```

## API Response Changes

### POST /upload Response
Now includes artist and song information:

```json
{
  "file_id": "43485f0b-7144-4081-974c-24d77efbe117",
  "filename": "43485f0b-7144-4081-974c-24d77efbe117.mp3",
  "artist": "Adele",
  "song": "Hello",
  "original_filename": "Adele - Hello (Official).mp3",
  "status": "completed",
  "message": "Successfully processed Adele - Hello",
  "tracks": [...],
  "download_url": "/download/43485f0b-7144-4081-974c-24d77efbe117"
}
```

### GET /songs Response
Now includes parsed metadata:

```json
{
  "songs": [
    {
      "file_id": "43485f0b-7144-4081-974c-24d77efbe117",
      "filename": "43485f0b-7144-4081-974c-24d77efbe117.mp3",
      "artist": "Adele",
      "song": "Hello",
      "display_name": "Adele - Hello",
      "size_bytes": 29475028,
      "has_karaoke": true,
      "karaoke_url": "/karaoke/43485f0b-7144-4081-974c-24d77efbe117"
    }
  ],
  "count": 1
}
```

## Progress Messages

Upload progress messages now show parsed artist and song:

```
Starting upload: Adele - Hello
Upload complete: Adele - Hello
Successfully processed Adele - Hello
```

## Testing Examples

### Test Filename Parsing
```python
# Test various formats
parse_artist_song("Adele - Hello.mp3")
# → {'artist': 'Adele', 'song': 'Hello'}

parse_artist_song("The Beatles - Hey Jude (Remastered).wav")
# → {'artist': 'The Beatles', 'song': 'Hey Jude'}

parse_artist_song("Song Without Artist.mp3")
# → {'artist': 'Unknown Artist', 'song': 'Song Without Artist'}

parse_artist_song("Artist-Song[Official Video].flac")
# → {'artist': 'Artist', 'song': 'Song'}
```

### Upload with curl
```bash
# Upload a properly named file
curl -F "file=@Adele - Hello.mp3" \
     -F "auto_process=true" \
     http://localhost:5000/upload

# Response will include:
# "artist": "Adele"
# "song": "Hello"
# "message": "Successfully processed Adele - Hello"
```

## Benefits

1. **Better Organization**: Files are automatically tagged with artist and song
2. **Improved UI**: Frontends can display "Artist - Song" instead of UUIDs
3. **Search & Filter**: Easy to search by artist or song name
4. **Karaoke Display**: Shows proper titles in karaoke player
5. **Metadata Preservation**: Original filename metadata is preserved

## Backwards Compatibility

- **Existing files**: Will show "Unknown Artist" / "Untitled" until re-uploaded
- **Old metadata**: No breaking changes to existing API structure
- **Gradual migration**: As files are re-uploaded, they'll get proper metadata

## Future Enhancements

Potential improvements:
- Support for "Artist_Song.ext" (underscore separator)
- Extract year from filename: "Artist - Song (2023).mp3"
- Genre detection from folder structure
- Integration with music databases (MusicBrainz, Spotify API)
- Automatic metadata correction/suggestion

## Notes

- **Case sensitivity**: Preserved as-is from filename
- **Special characters**: Allowed in artist/song names
- **Non-ASCII**: Full UTF-8 support (e.g., "Björk - Jóga.mp3" works correctly)
- **Performance**: Parsing adds negligible overhead (~1ms per file)
