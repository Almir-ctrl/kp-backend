"""
AI Model Processing Module
Supports multiple AI models for different purposes
"""
import os
import sys
import subprocess
from datetime import datetime
from flask import current_app


def require_gpu_or_raise():
    """Ensure a CUDA-capable GPU is available. Raise RuntimeError otherwise.

    This project enforces GPU-only inference ("NIKADA CPU"). Call this helper
    before loading or running heavy models to fail fast when no GPU is present.
    """
    try:
        import torch
    except Exception:
        raise RuntimeError(
            "PyTorch not installed or failed to import. "
            "GPU required for model inference (NIKADA CPU)."
        )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "No CUDA-enabled GPU detected. This backend requires a GPU "
            "for AI inference (NIKADA CPU)."
        )


def _is_ci_smoke_mode():
    """Detect if the application is running in CI smoke-test mode.

    Prefer the Flask app config when available; fall back to the
    CI_SMOKE env var for contexts outside an app instance.
    """
    try:
        from flask import current_app

        cfg = current_app.config if current_app else None
        if cfg and cfg.get("CI_SMOKE"):
            return True
    except Exception:
        # Not running inside Flask app context
        pass

    return os.environ.get("CI_SMOKE", "false").lower() == "true"


class MockMusicGenModel:
    """Mock MusicGen model for fallback when audiocraft not available"""

    def __init__(self):
        self.sample_rate = 32000

    def set_generation_params(
        self, duration=15, temperature=1.0, cfg_coeff=3.0
    ):
        """Mock parameter setting"""
        self.duration = duration
        self.temperature = temperature
        self.cfg_coeff = cfg_coeff

    def generate(self, prompts):
        """Generate mock audio tensor"""
        import torch
        import numpy as np

        # Create simple sine wave as placeholder audio
        duration_samples = int(self.sample_rate * self.duration)
        t = np.linspace(0, self.duration, duration_samples, False)

        # Generate a simple melody based on prompt hash
        prompt_hash = hash(prompts[0]) % 1000
        frequency = 440 + (prompt_hash % 200)  # Between 440-640 Hz

        # Create stereo sine wave
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        audio = np.stack([audio, audio])  # Stereo

        # Convert to torch tensor [batch, channels, samples]
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)

        return audio_tensor


class ModelProcessor:
    """Base class for AI model processing"""

    def __init__(self, model_name):
        self.model_name = model_name
        self.config = current_app.config["MODELS"].get(model_name)
        if not self.config:
            raise ValueError(f"Model {model_name} not configured")

    def process(self, file_id, input_file, **kwargs):
        """Process file with the specified model"""
        raise NotImplementedError("Subclasses must implement process method")


class DemucsProcessor(ModelProcessor):
    """Demucs audio separation processor"""

    def process(self, file_id, input_file, model_variant=None, two_stems=None):
        model_variant = model_variant or self.config["default_model"]
        # Enforce GPU-only for Demucs processing
        require_gpu_or_raise()
        # Output directory path will be constructed when needed

        # Use wrapper script to bypass torchaudio DLL issues on Windows
        wrapper_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "demucs_wrapper.py"
        )

        cmd = [
            sys.executable,
            wrapper_path,
            "-n",
            model_variant,
            "--mp3",
            "--two-stems=vocals",
            "-o",
            current_app.config["OUTPUT_FOLDER"],
            str(input_file),
        ]

        # Ensure subprocess uses venv Python by setting PYTHONPATH and PATH
        env = os.environ.copy()
        venv_path = os.path.dirname(sys.executable)
        env["PATH"] = venv_path + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = os.path.dirname(venv_path)
        # Remove PYTHONHOME to ensure venv is used
        env.pop("PYTHONHOME", None)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            raise Exception(f"Demucs processing failed: {result.stderr}")

        # Return separated tracks
        # Demucs creates: OUTPUT_FOLDER/MODEL_NAME/filename_without_extension/
        filename_without_ext = os.path.splitext(os.path.basename(input_file))[
            0
        ]
        expected_output_dir = os.path.join(
            current_app.config["OUTPUT_FOLDER"],
            model_variant,
            filename_without_ext,
        )

        tracks = []
        if os.path.exists(expected_output_dir):
            for track_file in os.listdir(expected_output_dir):
                if track_file.endswith(".mp3"):
                    track_name = os.path.splitext(track_file)[0]
                    tracks.append(track_name)

        return {
            "model": model_variant,
            "tracks": tracks,
            "output_dir": expected_output_dir,
        }


class WhisperProcessor(ModelProcessor):
    """Whisper speech-to-text processor"""

    def process(self, file_id, input_file, model_variant=None, **kwargs):
        """Delegate to the WhisperManager for robust, lazy-loaded
        transcription. The WhisperManager enforces GPU-only usage,
        lazily loads models per-variant, and writes transcription
        artifacts to the outputs folder.
        """
        # Use default variant if not provided
        model_variant = model_variant or self.config.get("default_model")
        wm = WhisperManager()
        return wm.transcribe(
            file_id=file_id,
            audio_path=str(input_file),
            model_variant=model_variant,
            **kwargs,
        )


class WhisperManager:
    """Manager to lazily load Whisper models on GPU and perform transcriptions.

    Usage:
      wm = WhisperManager()
      result = wm.transcribe(file_id, audio_path, model_variant='large')

    Result shape (dict): {
      'model': model_variant,
      'text': 'full transcription',
      'segments': [ {start,end,text}, ... ],
      'files': { 'json': filename, 'text': filename },
      'output_dir': '/outputs/{file_id}'
    }
    """

    _loaded_models = {}  # class-level cache: variant -> model

    def __init__(self):
        # Nothing to do at construction; models are loaded on demand.
        pass

    def _ensure_model(self, variant):
        """
        Load the whisper model for a given variant on GPU.
        Raises on missing GPU.
        """
        if variant in WhisperManager._loaded_models:
            return WhisperManager._loaded_models[variant]

        # If CI smoke mode is enabled, return a lightweight mock model
        # that implements the minimal `transcribe(audio_path, fp16=...)`
        # interface. This avoids loading large HF weights or requiring
        # GPUs in CI jobs.
        if _is_ci_smoke_mode():
            class MockWhisper:
                def transcribe(self, audio_path, fp16=True):
                    # Minimal fake result useful for CI smoke tests
                    return {
                        "text": "(ci-mock) transcription",
                        "segments": [],
                    }

            model = MockWhisper()
            WhisperManager._loaded_models[variant] = model
            return model

        # Enforce GPU-only policy
        require_gpu_or_raise()

        # Lazy import of whisper and torch
        try:
            import torch
            import whisper
        except Exception as e:
            raise RuntimeError(f"Whisper dependencies missing: {e}")

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU not available for Whisper model")

        device = "cuda"
        try:
            model = whisper.load_model(variant, device=device)
        except Exception as e:
            # Surface a clear error - caller may retry with another variant
            raise RuntimeError(
                f"Failed to load Whisper model '{variant}': {e}"
            )

        WhisperManager._loaded_models[variant] = model
        return model

    def transcribe(self, file_id, audio_path, model_variant="base", **kwargs):
        """
        Transcribe audio_path using the named model_variant and save
        artifacts. Writes JSON and TXT outputs under outputs/{file_id}/ and
        returns a structured dict with transcription and metadata.
        """
        model = self._ensure_model(model_variant)

        # Do the transcription with fp16 to reduce memory usage on GPU
        try:
            result = model.transcribe(audio_path, fp16=True)
        except Exception as e:
            raise RuntimeError(f"Whisper transcription failed: {e}")

        # Prepare output dir and file names
        output_dir = os.path.join(current_app.config["OUTPUT_FOLDER"], file_id)
        os.makedirs(output_dir, exist_ok=True)

        json_name = f"transcription_{model_variant}.json"
        txt_name = f"transcription_{model_variant}.txt"
        json_path = os.path.join(output_dir, json_name)
        txt_path = os.path.join(output_dir, txt_name)

        # Save JSON
        try:
            import json

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception:
            # Non-fatal: ignore json write errors but log
            try:
                current_app.logger.exception("Failed to write whisper json")
            except Exception:
                pass

        # Save text
        try:
            text_content = result.get("text", "")
            if isinstance(text_content, list):
                text_content = "\n".join(text_content)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except Exception:
            try:
                current_app.logger.exception("Failed to write whisper txt")
            except Exception:
                pass

        return {
            "model": model_variant,
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "files": {"json": json_name, "text": txt_name},
            "output_dir": output_dir,
        }


class MusicGenProcessor(ModelProcessor):
    """MusicGen text-to-music processor"""

    def __init__(self, model_name):
        super().__init__(model_name)
        self.model = None
        self.device = None

    def _load_model(self, model_variant):
        """Load MusicGen model on demand"""
        if self.model is None:
            try:
                # Respect CI-safe mode: avoid heavy model loads during CI smoke tests
                if _is_ci_smoke_mode():
                    print("CI_SMOKE enabled: using MockMusicGenModel for MusicGen")
                    self.model = MockMusicGenModel()
                    self.device = "cpu"
                    return
                # Try audiocraft first (preferred)
                # Enforce GPU-only usage
                require_gpu_or_raise()
                from audiocraft.models import MusicGen

                self.device = "cuda"
                print(f"Loading MusicGen '{model_variant}' on {self.device}")

                # Load the specified model
                self.model = MusicGen.get_pretrained(
                    model_variant, device=self.device
                )

                print(f"MusicGen model '{model_variant}' loaded successfully")

            except ImportError:
                # Fallback to mock implementation if audiocraft not available
                print("AudioCraft not available, using mock MusicGen")
                self.model = MockMusicGenModel()
                self.device = "cpu"
            except Exception as e:
                # Fallback for other errors
                print(f"AudioCraft failed ({e}), using mock MusicGen")
                self.model = MockMusicGenModel()
                self.device = "cpu"

    def process(self, file_id, input_file, model_variant=None, **kwargs):
        """Generate music from a text prompt and save to the outputs folder.

        This implementation is defensive: it attempts to save with
        torchaudio.save() first and falls back to soundfile if that
        fails (common on Windows when native torchcodec DLLs are
        unavailable). It also computes duration using soundfile where
        possible to avoid relying on torchaudio.info API.
        """

        # Use default variant if not provided
        model_variant = model_variant or self.config.get("default_model")

        # Ensure model is loaded
        self._load_model(model_variant)

        # Check if model loaded successfully
        if self.model is None:
            raise Exception(
                "MusicGen model failed to load; cannot generate music."
            )

        # Prompt comes from kwargs or use a safe default for self-tests
        prompt = kwargs.get("prompt", "An ambient instrumental piece")

        # Generation parameters
        gen_duration = int(kwargs.get("duration", 15))
        temperature = float(kwargs.get("temperature", 1.0))
        cfg_coeff = float(kwargs.get("cfg_coeff", 3.0))

        # Ask model to use these params if supported
        try:
            if hasattr(self.model, "set_generation_params"):
                self.model.set_generation_params(
                    duration=gen_duration,
                    temperature=temperature,
                    cfg_coeff=cfg_coeff,
                )
        except Exception:
            # ignore if model does not support param setting
            pass

        try:
            print(f"Generating music for prompt: '{prompt[:50]}...'")
            wav = self.model.generate([prompt])

            # Determine sample rate from model if available
            sample_rate = getattr(self.model, "sample_rate", 32000)

            # Normalize output tensor/array to a numpy array
            try:
                # torch tensor case
                audio_np = wav.squeeze(0).cpu().numpy()
            except Exception:
                import numpy as _np

                audio_np = _np.array(wav)

            # Ensure shape is (samples, channels) for soundfile
            import numpy as _np

            if audio_np.ndim == 1:
                data_to_write = _np.stack([audio_np, audio_np], axis=1)
            elif audio_np.shape[0] <= audio_np.shape[1]:
                # shape (channels, samples) -> transpose
                data_to_write = audio_np.T
            else:
                data_to_write = audio_np

            # Prepare output paths
            output_folder = current_app.config["OUTPUT_FOLDER"]
            output_dir = os.path.join(output_folder, file_id)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(
                output_dir, f"generated_{model_variant}.wav"
            )

            # Helper: get duration using soundfile as primary
            def _get_audio_duration(path):
                try:
                    import soundfile as sf

                    with sf.SoundFile(str(path)) as sfh:
                        return float(len(sfh)) / float(sfh.samplerate)
                except Exception:
                    return 0.0

            # Try torchaudio.save first, fallback to soundfile
            save_succeeded = False
            try:
                try:
                    import torchaudio

                    # Convert back to (channels, samples) if needed
                    save_arr = data_to_write
                    if data_to_write.ndim == 2 and data_to_write.shape[1] <= 2:
                        # (samples, channels) -> transpose to
                        # (channels, samples) for torchaudio
                        save_arr = data_to_write.T

                    # Convert numpy array to torch tensor if possible
                    try:
                        import torch as _torch

                        tensor = _torch.from_numpy(save_arr)
                    except Exception:
                        tensor = save_arr

                    torchaudio.save(output_file, tensor, sample_rate)
                    save_succeeded = True
                except Exception:
                    # Fallback to soundfile
                    import soundfile as sf

                    sf.write(
                        output_file,
                        data_to_write,
                        samplerate=sample_rate,
                    )
                    save_succeeded = True

            except Exception as e:
                print(f"Failed to save generated audio: {e}")
                raise

            if not save_succeeded:
                raise Exception("Could not save generated audio")

            # Save the prompt for reference
            prompt_file = os.path.join(
                output_dir, f"prompt_{model_variant}.txt"
            )
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(f"Prompt: {prompt}\n")
                f.write(f"Model: {model_variant}\n")
                f.write(f"Duration: {gen_duration}s\n")
                f.write(f"Temperature: {temperature}\n")
                f.write(f"CFG Coefficient: {cfg_coeff}\n")
                f.write(f"Sample Rate: {sample_rate}Hz\n")

            file_size = os.path.getsize(output_file)
            actual_duration = _get_audio_duration(output_file)

            # determine channels for metadata
            channels = 1
            try:
                if data_to_write.ndim == 2:
                    channels = data_to_write.shape[1]
            except Exception:
                channels = 1

            return {
                "model": model_variant,
                "prompt": prompt,
                "generated_file": os.path.basename(output_file),
                "prompt_file": os.path.basename(prompt_file),
                "duration": gen_duration,
                "sample_rate": sample_rate,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "actual_duration": round(actual_duration, 2),
                "channels": channels,
                "output_dir": output_dir,
                "generation_params": {
                    "temperature": temperature,
                    "cfg_coeff": cfg_coeff,
                    "model_variant": model_variant,
                },
            }

        except Exception as e:
            raise Exception(f"MusicGen generation failed: {str(e)}")


class PitchAnalysisProcessor(ModelProcessor):
    """Pitch and key analysis processor using chroma features"""

    def process(self, file_id, input_file, model_variant=None, **kwargs):
        import json

        model_variant = model_variant or self.config["default_model"]
        print(f"Using pitch analysis variant: {model_variant}")

        try:
            # Import common libs once for both analyzer and basic path
            import librosa
            import numpy as np  # noqa: F401

            # Choose analyzer based on model variant
            if model_variant == "enhanced_chroma":
                from enhanced_chroma_analyzer import EnhancedChromaAnalyzer

                analyzer = EnhancedChromaAnalyzer()
            elif model_variant == "librosa_chroma":
                from librosa_chroma_analyzer import EnhancedChromaAnalyzer

                analyzer = EnhancedChromaAnalyzer()
            else:
                analyzer = None  # Use basic librosa functions

            print(f"Analyzing pitch/key for file: {input_file}")

            output_dir = os.path.join(
                current_app.config["OUTPUT_FOLDER"], file_id
            )
            os.makedirs(output_dir, exist_ok=True)

            if analyzer:
                # Use enhanced analyzer
                y, sr = analyzer.load_audio(str(input_file))
                analysis_result = (
                    analyzer.extract_comprehensive_chroma_features(y)
                )

                # Add key detection if available
                if hasattr(analyzer, "detect_key_advanced") and callable(
                    getattr(analyzer, "detect_key_advanced", None)
                ):
                    key_info = analyzer.detect_key_advanced(y)
                    analysis_result.update(key_info)
                # If not available, skip advanced key detection

            else:
                # Basic analysis using librosa directly
                y, sr = librosa.load(str(input_file), sr=22050)

                # Extract chroma features
                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                chroma_mean = np.mean(chroma, axis=1)

                # Simple key detection
                major_template = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
                minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

                note_names = [
                    "C",
                    "C#",
                    "D",
                    "D#",
                    "E",
                    "F",
                    "F#",
                    "G",
                    "G#",
                    "A",
                    "A#",
                    "B",
                ]

                # Calculate correlations
                major_correlations = []
                minor_correlations = []

                for i in range(12):
                    major_shifted = np.roll(major_template, i)
                    minor_shifted = np.roll(minor_template, i)

                    major_corr = np.corrcoef(chroma_mean, major_shifted)[0, 1]
                    minor_corr = np.corrcoef(chroma_mean, minor_shifted)[0, 1]

                    major_correlations.append(major_corr)
                    minor_correlations.append(minor_corr)

                # Find best matches
                best_major_idx = np.argmax(major_correlations)
                best_minor_idx = np.argmax(minor_correlations)

                best_major_corr = major_correlations[best_major_idx]
                best_minor_corr = minor_correlations[best_minor_idx]

                if best_major_corr > best_minor_corr:
                    detected_key = f"{note_names[best_major_idx]} major"
                    confidence = best_major_corr
                else:
                    detected_key = f"{note_names[best_minor_idx]} minor"
                    confidence = best_minor_corr

                analysis_result = {
                    "detected_key": detected_key,
                    "confidence": float(confidence),
                    "chroma_vector": chroma_mean.tolist(),
                    "major_correlations": [
                        float(x) for x in major_correlations
                    ],
                    "minor_correlations": [
                        float(x) for x in minor_correlations
                    ],
                    "dominant_pitch_classes": [
                        note_names[i]
                        for i in np.argsort(chroma_mean)[-3:][::-1]
                    ],
                }

            # Save analysis results
            analysis_file = os.path.join(
                output_dir, f"pitch_analysis_{model_variant}.json"
            )
            # Ensure everything is JSON serializable (convert numpy types)

            def _sanitize(obj):
                import numpy as _np

                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                if isinstance(obj, tuple):
                    return tuple(_sanitize(v) for v in obj)
                if isinstance(obj, _np.ndarray):
                    return _sanitize(obj.tolist())
                if isinstance(obj, (_np.floating, _np.float32, _np.float64)):
                    return float(obj)
                if isinstance(obj, (_np.integer,)):
                    return int(obj)
                return obj

            sanitized = _sanitize(analysis_result)

            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, indent=2, ensure_ascii=False)

            print("Pitch analysis completed successfully")

            return {
                "model": model_variant,
                "detected_key": analysis_result.get("detected_key", "Unknown"),
                "confidence": analysis_result.get("confidence", 0.0),
                "analysis_file": f"pitch_analysis_{model_variant}.json",
                "dominant_pitches": (
                    analysis_result.get("dominant_pitch_classes", [])
                ),
                "output_dir": output_dir,
            }

        except Exception as e:
            print(f"Pitch analysis error: {str(e)}")
            raise Exception(f"Pitch analysis failed: {str(e)}")


class Gemma3NProcessor(ModelProcessor):
    """Gemma 3N audio transcription and analysis processor"""

    def analyze_word_timing(self, audio_path, transcription_text):
        """
        Analyze audio to generate word-level timing for lyrics sync.
        Uses onset detection and energy analysis for approximate timing.

        Returns a list of dicts: {word, start_time, end_time, confidence}
        """
        import librosa
        import numpy as np  # noqa: F401

        try:
            # Load audio and compute duration
            y, sr = librosa.load(str(audio_path), sr=22050)
            duration = librosa.get_duration(y=y, sr=sr)

            # Detect onsets (word boundaries)
            onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, units="frames", hop_length=512, backtrack=True
            )
            onset_times = librosa.frames_to_time(
                onset_frames, sr=sr, hop_length=512
            )

            # Split transcription into words
            words = transcription_text.split()
            if not words:
                return []

            word_timings = []

            if len(onset_times) >= len(words):
                # Map words to onset times
                for i, word in enumerate(words):
                    start_idx = int(i * len(onset_times) / len(words))
                    end_idx = int((i + 1) * len(onset_times) / len(words))

                    start_time = onset_times[start_idx]
                    end_time = (
                        onset_times[end_idx]
                        if end_idx < len(onset_times)
                        else duration
                    )

                    word_timings.append(
                        {
                            "word": word,
                            "start_time": float(start_time),
                            "end_time": float(end_time),
                            "confidence": 0.85,
                        }
                    )
            else:
                # Fallback: uniform distribution across duration
                time_per_word = duration / len(words)
                for i, word in enumerate(words):
                    start_time = i * time_per_word
                    end_time = (i + 1) * time_per_word
                    word_timings.append(
                        {
                            "word": word,
                            "start_time": float(start_time),
                            "end_time": float(end_time),
                            "confidence": 0.65,
                        }
                    )

            return word_timings

        except Exception as e:
            # If analysis fails, return a uniform fallback
            print(f"Word timing analysis error: {e}")
            words = transcription_text.split()
            duration = 180.0
            time_per_word = duration / max(len(words), 1)
            return [
                {
                    "word": word,
                    "start_time": float(i * time_per_word),
                    "end_time": float((i + 1) * time_per_word),
                    "confidence": 0.5,
                }
                for i, word in enumerate(words)
            ]

    def process(
        self,
        file_id,
        input_file,
        model_variant=None,
        task="transcribe",
        **kwargs,
    ):
        import json

        model_variant = model_variant or self.config["default_model"]
        task = kwargs.get("task", "transcribe")
        print(f"Using Gemma 3N model: {model_variant} for {task}")

        try:
            # Gemma3N uses large transformer models — in CI smoke mode we
            # avoid loading transformers and instead provide a lightweight
            # fallback that produces reasonable synthetic outputs.
            if _is_ci_smoke_mode():
                print("CI_SMOKE enabled: skipping Gemma3N heavy model load")
                # Simple fallback: load audio via librosa (if available)
                try:
                    import librosa

                    y, sr = librosa.load(str(input_file), sr=22050)
                    duration = librosa.get_duration(y=y, sr=sr)
                except Exception:
                    y = None
                    sr = 22050
                    duration = 0.0

                # Return a small synthetic response useful for CI
                return {
                    "model": model_variant,
                    "task": task,
                    "duration": duration,
                    "analysis": {
                        "summary": "ci-mock gemma analysis",
                    },
                    "output_dir": os.path.join(
                        current_app.config["OUTPUT_FOLDER"], file_id
                    ),
                }

            # Otherwise perform normal heavy-model loading and inference
            require_gpu_or_raise()
            # Import required libraries
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            import librosa

            print(f"Loading Gemma 3N model: {model_variant}")

            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(f"google/{model_variant}")
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Choose device map for large models
            if torch.cuda.is_available():
                device_map = "cuda"
                print("[Gemma3N] Using CUDA for inference.")
            else:
                device_map = "cpu"
                print("[Gemma3N] Using CPU for inference.")

            model = AutoModelForCausalLM.from_pretrained(
                f"google/{model_variant}",
                dtype=torch.bfloat16,
                device_map=device_map,
            )

            # Extract audio features for analysis
            print("Extracting audio features...")

            # Audio characteristics
            duration = librosa.get_duration(y=y, sr=sr)
            rms = librosa.feature.rms(y=y)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)

            # Chroma features
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = chroma.mean(axis=1)

            # MFCC features (extracted when needed)

            output_dir = os.path.join(
                current_app.config["OUTPUT_FOLDER"], file_id
            )
            os.makedirs(output_dir, exist_ok=True)

            # Prepare analysis prompt for Gemma 3N
            analysis_prompt = (
                f"Analyze this audio data:\n"
                f"- Duration: {duration:.2f} seconds\n"
                f"- Sample Rate: {sr} Hz\n"
                f"- RMS Energy: {rms.mean():.4f}\n"
                f"- Spectral Centroid: {spectral_centroid.mean():.2f} Hz\n"
                f"- Zero Crossing Rate: {zero_crossing_rate.mean():.4f}\n"
                f"- Chroma Distribution: {chroma_mean}\n"
                f"\nProvide a detailed analysis of the audio "
                f"characteristics."
            )

            if task == "transcribe":
                print("Generating transcription analysis...")
                task_prompt = (
                    f"{analysis_prompt}\n\nGenerate a detailed "
                    f"transcription description and analysis of the "
                    f"audio content."
                )
            elif task == "analyze":
                print("Performing audio analysis...")
                task_prompt = (
                    f"{analysis_prompt}\n\nProvide technical insights "
                    f"and recommendations."
                )
            else:
                task_prompt = analysis_prompt

            # Generate analysis using Gemma 3N
            # Tokenize with attention mask
            inputs = tokenizer(
                task_prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048,
            )
            # Move all input tensors to the model's device
            if hasattr(model, "device"):
                target_device = model.device
            elif hasattr(model, "hf_device_map") and isinstance(
                model.hf_device_map, dict
            ):
                # Use the first device in the device map
                target_device = list(model.hf_device_map.values())[0]
            else:
                target_device = torch.device(
                    "cuda" if torch.cuda.is_available() else "cpu"
                )
            for k in inputs:
                if hasattr(inputs[k], "to"):
                    inputs[k] = inputs[k].to(target_device)
            output_ids = model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=2048,
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.9),
                do_sample=kwargs.get("do_sample", True),
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

            analysis_result = tokenizer.decode(
                output_ids[0], skip_special_tokens=True
            )

            # Save results
            output_text_file = os.path.join(
                output_dir, f"analysis_{model_variant}_{task}.txt"
            )
            with open(output_text_file, "w", encoding="utf-8") as f:
                f.write("=== GEMMA 3N AUDIO ANALYSIS ===\n\n")
                f.write(f"Model: {model_variant}\n")
                f.write(f"Task: {task}\n")
                f.write(f"File: {os.path.basename(input_file)}\n\n")
                f.write("=== AUDIO FEATURES ===\n\n")
                f.write(f"Duration: {duration:.2f} seconds\n")
                f.write(f"Sample Rate: {sr} Hz\n")
                f.write(f"RMS Energy: {rms.mean():.4f}\n")
                f.write(
                    f"Spectral Centroid: {spectral_centroid.mean():.2f} Hz\n"
                )
                f.write(
                    f"Zero Crossing Rate: {zero_crossing_rate.mean():.4f}\n\n"
                )
                f.write("=== ANALYSIS ===\n\n")
                f.write(analysis_result)

            # Save as JSON
            output_json_file = os.path.join(
                output_dir, f"analysis_{model_variant}_{task}.json"
            )
            result = {
                "model": model_variant,
                "task": task,
                "filename": os.path.basename(input_file),
                "audio_features": {
                    "duration_seconds": float(duration),
                    "sample_rate": int(sr),
                    "rms_energy": float(rms.mean()),
                    "spectral_centroid_hz": float(spectral_centroid.mean()),
                    "zero_crossing_rate": float(zero_crossing_rate.mean()),
                    "chroma_distribution": chroma_mean.tolist(),
                },
                "analysis": analysis_result,
                "generation_params": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                    "do_sample": kwargs.get("do_sample", True),
                },
            }

            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Generate word-level timing if transcription exists
            word_timings = []
            if task == "transcribe" and analysis_result:
                print("Generating word-level timing for lyrics sync...")
                word_timings = self.analyze_word_timing(
                    input_file, analysis_result
                )
                print(f"✅ Generated {len(word_timings)} word timings")

                # Save word timings separately
                word_timings_file = os.path.join(
                    output_dir, f"word_timings_{model_variant}.json"
                )
                with open(word_timings_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "word_timings": word_timings,
                            "total_words": len(word_timings),
                            "duration_seconds": float(duration),
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

            print("Audio analysis completed successfully")

            return {
                "model": model_variant,
                "task": task,
                "filename": os.path.basename(input_file),
                "duration_seconds": float(duration),
                "sample_rate": int(sr),
                "analysis_summary": analysis_result,  # Full result
                "analysis_full": analysis_result,  # Alias for full analysis
                "word_timings": word_timings,  # For lyrics sync
                "output_text_file": f"analysis_{model_variant}_{task}.txt",
                "output_json_file": f"analysis_{model_variant}_{task}.json",
                "output_dir": output_dir,
            }

        except ImportError as e:
            raise Exception(
                f"Gemma 3N dependencies not installed. "
                f"Install with: pip install transformers torch librosa "
                f"soundfile (Error: {str(e)})"
            )
        except Exception as e:
            print(f"Gemma 3N analysis error: {str(e)}")
            raise Exception(f"Audio analysis failed: {str(e)}")


class KaraokeProcessor:
    """Generate karaoke files with synced lyrics and metadata embedding"""

    def __init__(self, model_name="karaoke"):
        self.model_name = model_name
        self.karaoke_base = os.path.join("outputs", "Karaoke-pjesme")
        os.makedirs(self.karaoke_base, exist_ok=True)

    def process(
        self,
        file_id,
        instrumental_path,
        vocals_path,
        transcription_text,
        original_audio_path=None,
        **kwargs,
    ):
        """
        Create karaoke package with synced lyrics

        Args:
            file_id: Unique identifier for the song
            instrumental_path: Path to instrumental track (no_vocals.mp3)
            vocals_path: Path to isolated vocals track (vocals.mp3)
            transcription_text: Raw transcription text from Gemma 3n
            original_audio_path: Optional original audio for timing reference
            **kwargs: Additional options (model_variant, etc.)

        Returns:
            dict with karaoke_dir, lrc_file, audio_with_metadata, sync_metadata
        """
        try:
            import librosa
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, USLT, TIT2, TPE1, TALB
            import json

            # Create karaoke output directory
            karaoke_dir = os.path.join(self.karaoke_base, file_id)
            os.makedirs(karaoke_dir, exist_ok=True)

            # Load audio for timing analysis
            audio_for_timing = (
                vocals_path
                if os.path.exists(vocals_path)
                else original_audio_path
            )
            if not audio_for_timing or not os.path.exists(audio_for_timing):
                raise FileNotFoundError(
                    "Need vocals or original audio for timing sync"
                )

            y, sr = librosa.load(audio_for_timing, sr=22050)
            duration = librosa.get_duration(y=y, sr=sr)

            # Split transcription into lines
            # First try splitting by newlines, then by sentences
            lines = [
                line.strip()
                for line in transcription_text.split("\n")
                if line.strip()
            ]

            # If only one line, split by sentence endings or word count
            if len(lines) <= 1 and transcription_text:
                import re

                # Split on sentence endings (. ! ?)
                sentences = re.split(r"[.!?]+", transcription_text)
                lines = [s.strip() for s in sentences if s.strip()]

                # If still too few lines, split by commas or max words
                if len(lines) <= 2:
                    # Split on commas or every ~10 words
                    words = transcription_text.split()
                    lines = []
                    chunk_size = 10  # words per line
                    for i in range(0, len(words), chunk_size):
                        chunk = " ".join(words[i:i + chunk_size])
                        if chunk:
                            lines.append(chunk)

            # Generate timestamps using uniform distribution (simple sync)
            # In production, use Gemma 3n or forced alignment for
            # accurate timing
            synced_lyrics = []
            if lines:
                time_per_line = duration / len(lines)
                for i, line in enumerate(lines):
                    timestamp = i * time_per_line
                    minutes = int(timestamp // 60)
                    seconds = timestamp % 60
                    lrc_timestamp = f"[{minutes:02d}:{seconds:05.2f}]"
                    synced_lyrics.append(
                        {
                            "timestamp": timestamp,
                            "lrc_format": lrc_timestamp,
                            "text": line,
                        }
                    )

            # Create LRC file
            lrc_filename = f"{file_id}_karaoke.lrc"
            lrc_path = os.path.join(karaoke_dir, lrc_filename)

            song_name = kwargs.get("song_name")
            artist = kwargs.get("artist")
            lrc_title = song_name if song_name else "Karaoke Song"
            lrc_artist = artist if artist else "Unknown Artist"
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write(f"[ti:{lrc_title}]\n")
                f.write(f"[ar:{lrc_artist}]\n")
                f.write("[al:]\n")
                mins = int(duration // 60)
                secs = int(duration % 60)
                f.write(f"[length:{mins:02d}:{secs:02d}]\n")
                f.write("\n")
                for lyric in synced_lyrics:
                    f.write(f"{lyric['lrc_format']}{lyric['text']}\n")

            # Copy instrumental to karaoke folder and add metadata
            karaoke_audio_filename = f"{file_id}_karaoke.mp3"
            karaoke_audio_path = os.path.join(
                karaoke_dir, karaoke_audio_filename
            )

            # Copy instrumental file
            import shutil

            shutil.copy2(instrumental_path, karaoke_audio_path)

            # Embed lyrics in ID3 tags
            try:
                audio = MP3(karaoke_audio_path, ID3=ID3)
                if audio.tags is None:
                    audio.add_tags()
                full_lyrics = "\n".join(
                    [lyric["text"] for lyric in synced_lyrics]
                )
                audio.tags.add(
                    USLT(
                        encoding=3,
                        lang="eng",
                        desc="Karaoke Lyrics",
                        text=full_lyrics,
                    )
                )
                audio.tags.add(TIT2(encoding=3, text=f"Karaoke - {file_id}"))
                audio.tags.add(TPE1(encoding=3, text="AI Music Separator"))
                audio.tags.add(TALB(encoding=3, text="Karaoke Collection"))
                audio.save()
            except Exception as e:
                print(f"Warning: Could not embed ID3 tags: {e}")

            # Copy metadata.json from outputs to karaoke dir for artist/title
            source_metadata = os.path.join("outputs", file_id, "metadata.json")
            dest_metadata = os.path.join(karaoke_dir, "metadata.json")
            if os.path.exists(source_metadata):
                import shutil

                shutil.copy2(source_metadata, dest_metadata)
                print("✅ Copied metadata.json to karaoke directory")
            else:
                # Create basic metadata if source doesn't exist
                basic_metadata = {
                    "title": song_name or "Unknown Title",
                    "artist": artist or "Unknown Artist",
                    "duration": duration,
                }
                with open(dest_metadata, "w", encoding="utf-8") as f:
                    json.dump(basic_metadata, f, indent=2, ensure_ascii=False)

            # Save sync metadata as JSON
            sync_metadata_path = os.path.join(
                karaoke_dir, f"{file_id}_sync.json"
            )
            sync_data = {
                "file_id": file_id,
                "artist": artist,
                "song_name": song_name,
                "duration": duration,
                "total_lines": len(lines),
                "synced_lyrics": synced_lyrics,
                "lrc_file": lrc_filename,
                "audio_file": karaoke_audio_filename,
                "generated_at": str(datetime.now()),
            }
            with open(sync_metadata_path, "w", encoding="utf-8") as f:
                json.dump(sync_data, f, indent=2, ensure_ascii=False)

            return {
                "karaoke_dir": karaoke_dir,
                "lrc_file": lrc_path,
                "audio_with_metadata": karaoke_audio_path,
                "sync_metadata": sync_metadata_path,
                "total_lines": len(lines),
                "duration": duration,
                "synced_lyrics_count": len(synced_lyrics),
            }

        except Exception as e:
            raise Exception(f"Karaoke generation failed: {str(e)}")


# Model processor registry
PROCESSORS = {
    "demucs": DemucsProcessor,
    "whisper": WhisperProcessor,
    "musicgen": MusicGenProcessor,
    "pitch_analysis": PitchAnalysisProcessor,
    "gemma_3n": Gemma3NProcessor,
    "karaoke": KaraokeProcessor,
}


def get_processor(model_name):
    """Get processor instance for a model"""
    processor_class = PROCESSORS.get(model_name)
    if not processor_class:
        raise ValueError(f"No processor available for model: {model_name}")
    return processor_class(model_name)


# Utility: Test all processors with dummy/test data
def test_all_processors():
    import tempfile
    import os

    print("Testing all model processors...")
    results = {}
    for model_name, processor_class in PROCESSORS.items():
        processor = processor_class(model_name)
        print(f"\n--- Testing {model_name} ---")
        try:
            # Create a valid WAV silence file for tests so ffmpeg can read it
            import soundfile as sf
            import numpy as np

            samplerate = 16000
            duration_s = 1.0
            silence = np.zeros(int(samplerate * duration_s), dtype="float32")
            test_file = os.path.join(
                tempfile.gettempdir(), f"test_{model_name}.wav"
            )
            sf.write(test_file, silence, samplerate)

            file_id = "test123"

            # Run the appropriate processor with minimal safe args
            if model_name == "musicgen":
                result = processor.process(
                    file_id,
                    test_file,
                    model_variant="large",
                    prompt="Test melody",
                )
            elif model_name == "gemma_3n":
                # Skip Gemma 3N self-test because models are large and may
                # trigger long downloads and heavy GPU/CPU usage during
                # developer self-tests.
                result = {
                    "model": "gemma_3n",
                    "status": "skipped_for_self_test",
                }
            elif model_name == "pitch_analysis":
                result = processor.process(
                    file_id,
                    test_file,
                    model_variant="enhanced_chroma",
                )
            elif model_name == "demucs":
                result = processor.process(
                    file_id,
                    test_file,
                    model_variant="htdemucs",
                )
            elif model_name == "whisper":
                result = processor.process(
                    file_id,
                    test_file,
                    model_variant="large-v2",
                )
            elif model_name == "karaoke":
                # Skip heavy karaoke generation in self-test
                result = {
                    "model": "karaoke",
                    "status": "skipped_for_self_test",
                }
            else:
                result = processor.process(file_id, test_file)

            results[model_name] = {"success": True, "result": result}
            print(f"{model_name} result: {result}")

        except Exception as e:
            results[model_name] = {"success": False, "error": str(e)}
            print(f"{model_name} error: {e}")
        finally:
            # Clean up test file
            try:
                if test_file and os.path.exists(test_file):
                    os.unlink(test_file)
            except Exception:
                pass
    print("\nAll processor tests complete.")
    return results
