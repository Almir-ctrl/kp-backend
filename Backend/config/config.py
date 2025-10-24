import os


class Config:
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg'}

    # AI Models Configuration
    MODELS = {
        'demucs': {
            'default_model': 'htdemucs',
            'available_models': ['htdemucs', 'mdx_extra', 'mdx', 'mdx_q', 'mdx_extra_q'],
            'purpose': 'audio_separation',
            'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
        },
        # Example: Add other models here
        'whisper': {
            'default_model': 'medium',
            'available_models': ['tiny', 'base', 'small', 'medium', 'large'],
            'purpose': 'speech_to_text',
            'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
        },
        'musicgen': {
            'default_model': 'large',
            'available_models': ['small', 'medium', 'large'],
            'purpose': 'music_generation',
            'file_types': {'txt'}
        },
        'pitch_analysis': {
            'default_model': 'enhanced_chroma',
            'available_models': [
                'basic_chroma', 'enhanced_chroma', 'librosa_chroma'
            ],
            'purpose': 'pitch_key_detection',
            'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
        },
        'gemma_3n': {
            'default_model': 'gemma-2-9b-it',
            'available_models': [
                'gemma-2-2b-it', 'gemma-2-9b-it', 'gemma-2-27b-it'
            ],
            'purpose': 'audio_transcription_analysis',
            'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
        },
        'karaoke': {
            'default_model': 'full',
            'available_models': ['full', 'instrumental_only'],
            'purpose': 'karaoke_package_creation',
            'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
        }
    }

    # Backward compatibility
    DEMUCS_MODEL = MODELS['demucs']['default_model']
    # Whisper model selection via env var; can be a short name or HF repo
    WHISPER_MODEL = (
        os.environ.get('WHISPER_MODEL', MODELS['whisper']['default_model'])
    )
    # If set, the HF repo to download the model from
    # (e.g., openai/whisper-large-v2)
    WHISPER_MODEL_REPO = os.environ.get('WHISPER_MODEL_REPO', None)
    # Whether to use huggingface_hub snapshot download on startup
    WHISPER_USE_HF_DOWNLOAD = (
        os.environ.get('WHISPER_USE_HF_DOWNLOAD', 'false').lower() == 'true'
    )

    # Server settings - Production ready
    HOST = '0.0.0.0'  # Listen on all interfaces
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Create directories if they don't exist
    def __init__(self):
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(self.OUTPUT_FOLDER, exist_ok=True)

    # CI-safe mode: when true the app should avoid loading heavy models
    # and instead use lightweight mocks/stubs suitable for smoke tests in
    # CI environments where GPUs or large model files are not available.
    # Set CI_SMOKE=true in CI to enable.
    CI_SMOKE = os.environ.get('CI_SMOKE', 'false').lower() == 'true'
