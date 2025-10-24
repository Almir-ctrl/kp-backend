# DELETE Song Endpoint

## Overview
Added DELETE endpoint to remove songs and all associated files from the backend.

## Endpoint

### DELETE /songs/<file_id>

Deletes a song and all its associated files including:
- Uploaded audio file
- Metadata JSON
- Separation outputs (Demucs tracks)
- Transcription results
- Karaoke files

**URL**: `/songs/<file_id>`  
**Method**: `DELETE`  
**Auth**: None  
**CORS**: Full support with OPTIONS preflight

## Request

### URL Parameters
- `file_id` (required): The unique UUID of the song to delete

### Example
```bash
DELETE http://localhost:5000/songs/0e9ae407-1377-42d5-bc31-e455ee2c84e4
```

## Response

### Success (200 OK)
When files are successfully deleted:

```json
{
  "status": "success",
  "file_id": "0e9ae407-1377-42d5-bc31-e455ee2c84e4",
  "deleted": [
    "upload: 0e9ae407-1377-42d5-bc31-e455ee2c84e4.wav",
    "metadata: 0e9ae407-1377-42d5-bc31-e455ee2c84e4_metadata.json",
    "output: 0e9ae407-1377-42d5-bc31-e455ee2c84e4/",
    "separation: htdemucs/0e9ae407-1377-42d5-bc31-e455ee2c84e4/",
    "karaoke: Karaoke-pjesme/0e9ae407-1377-42d5-bc31-e455ee2c84e4/"
  ],
  "message": "Deleted 5 item(s)"
}
```

### Partial Success (200 OK with warnings)
When some files are deleted but others fail:

```json
{
  "status": "success",
  "file_id": "0e9ae407-1377-42d5-bc31-e455ee2c84e4",
  "deleted": [
    "upload: 0e9ae407-1377-42d5-bc31-e455ee2c84e4.wav",
    "metadata: 0e9ae407-1377-42d5-bc31-e455ee2c84e4_metadata.json"
  ],
  "warnings": [
    "Failed to delete output dir: Permission denied"
  ],
  "message": "Deleted 2 item(s)"
}
```

### Not Found (404)
When no files exist for the given file_id:

```json
{
  "status": "not_found",
  "file_id": "non-existent-id",
  "message": "No files found to delete",
  "errors": []
}
```

### Error (500)
When an unexpected error occurs:

```json
{
  "status": "error",
  "file_id": "0e9ae407-1377-42d5-bc31-e455ee2c84e4",
  "error": "Unexpected error message"
}
```

## What Gets Deleted

The endpoint searches for and deletes:

1. **Upload file**: `uploads/<file_id>.*` (any extension)
2. **Metadata**: `uploads/<file_id>_metadata.json`
3. **Output directory**: `outputs/<file_id>/` (transcription, analysis)
4. **Separation tracks**: `outputs/htdemucs*/<file_id>/` (vocals, no_vocals)
5. **Karaoke files**: `outputs/Karaoke-pjesme/<file_id>/` (LRC, MP3, JSON)

## CORS Support

The endpoint fully supports CORS preflight requests:

### OPTIONS /songs/<file_id>

Returns appropriate CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

## Lion's Roar Studio Integration

### Fetch API
```javascript
async function deleteSong(fileId) {
  try {
    const response = await fetch(`http://localhost:5000/songs/${fileId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      console.log(`Deleted: ${result.deleted.join(', ')}`);
      
      if (result.warnings) {
        console.warn('Warnings:', result.warnings);
      }
    } else if (result.status === 'not_found') {
      console.log('Song not found');
    } else {
      console.error('Delete failed:', result.error);
    }
    
    return result;
  } catch (error) {
    console.error('Failed to delete:', error);
    throw error;
  }
}

// Usage
await deleteSong('0e9ae407-1377-42d5-bc31-e455ee2c84e4');
```

### Axios
```javascript
import axios from 'axios';

async function deleteSong(fileId) {
  try {
    const response = await axios.delete(
      `http://localhost:5000/songs/${fileId}`
    );
    
    console.log('Deleted:', response.data.deleted);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      console.log('Song not found');
    } else {
      console.error('Delete failed:', error);
    }
    throw error;
  }
}
```

## Security Considerations

1. **No Authentication**: Currently no auth required (add if needed)
2. **Permanent Deletion**: Files are permanently deleted (no trash/recovery)
3. **Rate Limiting**: Consider adding rate limits to prevent abuse
4. **Validation**: File IDs are UUID format only

## Testing

### curl
```bash
# Test DELETE
curl -X DELETE http://localhost:5000/songs/0e9ae407-1377-42d5-bc31-e455ee2c84e4

# Test CORS preflight
curl -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: DELETE" \
  -v http://localhost:5000/songs/test-id
```

### Python
```python
import requests

# Delete a song
response = requests.delete(
    'http://localhost:5000/songs/0e9ae407-1377-42d5-bc31-e455ee2c84e4'
)

if response.status_code == 200:
    result = response.json()
    print(f"Deleted: {result['deleted']}")
elif response.status_code == 404:
    print("Song not found")
else:
    print(f"Error: {response.json()['error']}")
```

## Error Handling

The endpoint handles various error scenarios:

- **File locked**: Partial deletion with warnings
- **Permission denied**: Included in warnings array
- **Directory not empty**: Recursive deletion with `shutil.rmtree()`
- **Non-existent files**: Returns 404 with appropriate message

## Logging

All delete operations are logged:
```python
# Success
app.logger.info(f"Deleted song {file_id}: {len(deleted_items)} items")

# Partial
app.logger.warning(f"Partial delete for {file_id}: {warnings}")

# Error
app.logger.error(f"Failed to delete {file_id}: {error}")
```

## Future Enhancements

Potential improvements:
- Add authentication/authorization
- Implement soft delete (move to trash)
- Add batch delete endpoint: `DELETE /songs` with body `{file_ids: [...]}`
- Add dry-run mode: `DELETE /songs/<file_id>?dry_run=true`
- Emit WebSocket event for delete progress
- Add cascade delete option (delete related files only)

## Migration Notes

- Existing files are not affected until explicitly deleted
- Lion's Roar Studio should handle 404 gracefully for already-deleted songs
- Consider adding confirmation dialog in UI before deletion
