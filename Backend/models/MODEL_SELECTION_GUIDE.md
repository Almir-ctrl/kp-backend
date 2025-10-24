<!-- Pointer: moved to /part of AI separator backend/demucs/MULTI_MODEL_GUIDE.md -->

See canonical copy at: `/part of AI separator backend/demucs/MULTI_MODEL_GUIDE.md`
> This guide has moved to the part of AI separator backend area.

Canonical location:

- /part of AI separator backend/demucs/MULTI_MODEL_GUIDE.md

> NOTE: This file has been archived. The canonical, maintained copy of the model selection and multi-model guide lives at `/part of AI separator backend/demucs/MULTI_MODEL_GUIDE.md`.

If you need this file preserved at the old path for automation, open an issue with the script path and we'll add a compatibility pointer.
````markdown
# Advanced Model Selection Feature

## Overview

The Advanced Model Selection feature allows users to choose different AI models and their variations for audio processing tasks in Lion's Roar Karaoke Studio. This gives users fine-grained control over the trade-off between processing speed and output quality.

## Supported Models

### 1. Demucs (Music Source Separation)

Demucs is used for two tasks:
- **Vocal Separation**: Extract vocals and create an instrumental version
- **Stem Separation**: Separate audio into 4 tracks (vocals, drums, bass, other)

#### Available Variations:

| Variation | Name | Quality | Speed | Use Case |
|-----------|------|---------|-------|----------|
| `demucs` | Conv Demucs (Fast) | Medium | Fast | Quick tests |
| `htdemucs` | HT Demucs (Default) | High | Slow | Most use cases |
| `htdemucs_ft` | HT Demucs FT (Fine-tuned) | Highest | Slow | Best quality |
| `htdemucs_6s` | HT Demucs 6s | High | Slow | Balanced window |
| `tasnet` | TasNet (Lightweight) | Medium | Fastest | Resource-limited |
| `tasnet_extra` | TasNet Extra (Enhanced) | Med-High | Fast | Better TasNet |

### 2. Whisper (Speech Recognition & Transcription)

Whisper is used for:
- **Song Transcription**: Automatically transcribe lyrics with timestamps

#### Available Variations:

| Variation | Name | Quality | Speed | Memory | Parameters | Languages |
|-----------|------|---------|-------|--------|------------|-----------|
| `tiny` | Tiny | Low | Fastest | Low | ~39M | Multilingual |
| `tiny.en` | Tiny English | Low | Fastest | Low | ~39M | English only |
| `base` | Base (Default) | Medium | Fast | Low | ~74M | Multilingual |
| `base.en` | Base English | Medium | Fast | Low | ~74M | English only |
| `small` | Small | High | Medium | Medium | ~244M | Multilingual |
| `small.en` | Small English | High | Medium | Medium | ~244M | English only |
| `medium` | Medium | Very High | Slow | Medium | ~769M | Multilingual |
| `medium.en` | Medium English | Very High | Slow | Medium | ~769M | English only |
| `large` | Large (Highest) | Highest | Slowest | High | ~1550M | Multilingual |

**Note:** `.en` variants are optimized for English-language audio only and run faster than multilingual variants.

## Lion's Roar Studio Implementation

### Components

#### 1. **AdvancedToolsWindow.tsx** (Updated)
The main window component that displays the advanced tools interface.

**Changes:**
- Added state management for model and variation selection
- Integrated `ModelSelectorModal` component
- Passes model and variation to `processSongWithAdvancedTool`

**Key Functions:**
```typescript
handleVocalIsolation()        // Opens modal for vocal separation
handleStemSeparation()        // Opens modal for stem separation  
handleTranscription()         // Opens modal for transcription
handleVariationSelected()     // Called when user confirms a variation
```

#### 2. **ModelSelectorModal.tsx** (New)
A modal dialog that displays available model variations for selection.

**Features:**
- Fetches available models from `/models` endpoint
- Displays model variations with detailed specs
- Shows quality, speed, and memory metrics
- Radio button selection interface
- Confirm/Cancel actions

**Props:**
```typescript
interface ModelSelectorModalProps {
	isOpen: boolean;              // Whether modal is visible
	modelName: string;            // 'demucs' or 'whisper'
	onSelectVariation: (variation: string) => void;
	onCancel: () => void;
	isLoading?: boolean;          // Show loading state
}
```

### Workflow

1. User clicks a tool button (Vocal Separation, Stem Separation, or Transcribe)
2. `ModelSelectorModal` opens showing available variations
3. User selects a variation and clicks Confirm
4. Modal passes selected variation to `processSongWithAdvancedTool`
5. Processing begins with the specified model and variation

## AI separator backend Implementation

### New API Endpoints

#### 1. **GET /models**
Returns all available models and their variations.

**Response:**
```json
{
	"models": {
		"demucs": {
			"name": "Demucs - Stem Separation",
			"description": "...",
			"variations": {
				"htdemucs": {
					"name": "HT Demucs (Default)",
					"description": "...",
					"quality": "high",
					"speed": "slow"
				},
				// ... other variations
			},
			"default_variation": "htdemucs"
		},
		"whisper": {
			// ... similar structure
		}
	}
}
```

#### 2. **GET /models/<model_name>**
Returns details for a specific model.

**Parameters:**
- `model_name`: 'demucs' or 'whisper'

**Response:**
```json
{
	"model": "demucs",
	"details": {
		"name": "Demucs - Stem Separation",
		"description": "...",
		"variations": { ... },
		"default_variation": "htdemucs"
	}
}
```

#### 3. **POST /process/<model>/<file_id>** (Updated)
Starts processing with optional model variation.

**Request Body (Optional):**
```json
{
	"variation": "htdemucs_ft"  // Specify model variation
}
```

**Response:**
```json
{
	"message": "Processing started with demucs",
	"file_id": "uuid-string",
	"status": "queued",
	"model": "demucs",
	"variation": "htdemucs_ft"
}
```

### Updated Processing Functions

#### 1. **process_audio_async()**
```python
def process_audio_async(
		file_path: str,
		file_id: str,
		model: str,
		variation: str = None
):
		"""Process audio file asynchronously"""
		# Uses default variation if not specified
		if variation is None:
				variation = AVAILABLE_MODELS[model]['default_variation']
		# ... routes to appropriate processor
```

#### 2. **process_with_demucs()**
```python
def process_with_demucs(
		file_path: str,
		file_id: str,
		variation: str = 'htdemucs'
) -> bool:
		"""Process audio file with Demucs for stem separation"""
		# Uses specified Demucs variation
		model = demucs.api.load_model(variation)
		# ...
```

#### 3. **process_with_whisper()**
```python
def process_with_whisper(
		file_path: str,
		file_id: str,
		variation: str = 'base'
) -> bool:
		"""Process audio file with Whisper for transcription"""
		# Uses specified Whisper variation
		model = whisper.load_model(variation)
		# ...
```

````

