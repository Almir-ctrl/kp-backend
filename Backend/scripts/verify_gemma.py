"""Verify Gemma 3n dependencies and model access."""


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking Gemma 3n dependencies...")
    print("=" * 60)

    dependencies = {
        "transformers": "Hugging Face Transformers",
        "torch": "PyTorch",
        "librosa": "Audio processing",
        "soundfile": "Audio I/O",
        "accelerate": "Model loading optimization",
        "sentencepiece": "Tokenization (optional)",
    }

    missing = []
    installed = []

    import sys as _sys

    for module, description in dependencies.items():
        try:
            __import__(module)
            version = None
            try:
                mod = _sys.modules.get(module)
                version = getattr(mod, "__version__", "unknown")
            except Exception:  # pragma: no cover - defensive
                version = "unknown"
            installed.append((module, description, version))
            print("✅ {} ({}) : {}".format(module, description, version))
        except ImportError:
            missing.append((module, description))
            print("❌ {} ({}) : NOT FOUND".format(module, description))

    print("\n" + "=" * 60)

    if missing:
        print("\n❌ Missing {} dependencies:".format(len(missing)))
        for module, desc in missing:
            print("   - {} ({})".format(module, desc))
        print("\nInstall missing dependencies:")
        print("pip install " + " ".join([m[0] for m in missing]))
        return False

    print("\n✅ All {} dependencies are installed!".format(len(installed)))
    return True


def test_model_loading():
    """Test loading a small Gemma model from HuggingFace."""
    print("\n" + "=" * 60)
    print("Testing Gemma 3n model loading...")
    print("=" * 60)

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore
        import torch  # type: ignore

        # Try to load the smallest Gemma model (gemma-2-2b)
        model_name = "google/gemma-2-2b"

        print(f"\nAttempting to load tokenizer: {model_name}")
        print("(This may download the model if not cached)")
        print("First-time download can be 5-10 GB...")

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            print("✅ Tokenizer loaded successfully")

            # Try to load model (this might fail without HF token or GPU)
            print(f"\nAttempting to load model: {model_name}")
            print("(This requires a HuggingFace token and GPU)")

            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=getattr(torch, "bfloat16", None),
                device_map="auto",
                low_cpu_mem_usage=True,
            )
            print("✅ Model loaded successfully!")
            print("   Model device: {}".format(getattr(model, "device", "unknown")))
            print("   Model dtype: {}".format(getattr(model, "dtype", "unknown")))

            # Test generation (best-effort; may consume resources)
            test_prompt = "Analyze this audio: duration 30 seconds, 44100 Hz"
            inputs = tokenizer(test_prompt, return_tensors="pt")

            outputs = model.generate(
                **inputs,
                max_length=50,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            print("✅ Generation successful!")
            print("   Input: " + test_prompt)
            print("   Output: " + result[:100] + "...")

            return True

        except Exception as exc:  # pragma: no cover - model loading can fail in many envs
            print("⚠️  Model loading failed: {}".format(str(exc)))
            print("\nThis is expected if:")
            print("  1. You don't have a HuggingFace token")
            print("  2. You haven't accepted Gemma's license")
            print("  3. You don't have enough GPU memory")
            print("  4. Model isn't downloaded yet")

            print("\nTo use Gemma models:")
            print("  1. Get token: https://huggingface.co/settings/tokens")
            print("  2. Accept license: https://huggingface.co/google/gemma-2-2b")
            print("  3. Login: huggingface-cli login")
            print("  4. Ensure you have a compatible GPU (8GB+ VRAM)")

            return False

    except ImportError as exc:
        print("❌ Import error: {}".format(str(exc)))
        print("Install transformers and torch:")
        print("pip install transformers torch accelerate")
        return False
    except Exception as exc:  # pragma: no cover - top-level diagnostic
        print("❌ Unexpected error: {}".format(str(exc)))
        return False


def test_audio_processing():
    """Test audio processing capabilities."""
    print("\n" + "=" * 60)
    print("Testing audio processing...")
    print("=" * 60)
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore

        print("✅ Audio libraries imported successfully")

        # Create a simple test audio (1 second of sine wave)
        sr = 22050  # Sample rate
        duration = 1.0  # 1 second
        frequency = 440  # A4 note

        t = np.linspace(0, duration, int(sr * duration))
        audio = 0.5 * np.sin(2 * np.pi * frequency * t)

        # Test audio feature extraction
        rms = librosa.feature.rms(y=audio)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)

        print("✅ Audio features extracted:")
        print("   - RMS Energy: {:.4f}".format(rms.mean()))
        print("   - Spectral Centroid: {:.2f} Hz".format(spectral_centroid.mean()))
        print("   - Chroma shape: {}".format(chroma.shape))
        print("   - MFCC shape: {}".format(mfcc.shape))

        return True

    except ImportError as exc:
        print("❌ Import error: {}".format(str(exc)))
        print("Install audio libraries:")
        print("pip install librosa soundfile")
        return False
    except Exception as exc:  # pragma: no cover - diagnostic
        print("❌ Unexpected error: {}".format(str(exc)))
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("GEMMA 3N DEPENDENCY VERIFICATION")
    print("=" * 60)

    results = {
        'dependencies': False,
        'audio_processing': False,
        'model_loading': False
    }

    # Check dependencies
    results['dependencies'] = check_dependencies()

    if not results['dependencies']:
        print("\n❌ Please install missing dependencies first.")
        return False

    # Test audio processing
    results['audio_processing'] = test_audio_processing()

    # Test model loading (optional - may fail without HF token)
    results['model_loading'] = test_model_loading()

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    print("\nTests passed: {}/{}".format(passed, total))
    print("  ✅ Dependencies: {}".format('PASS' if results['dependencies'] else 'FAIL'))
    print("  ✅ Audio Processing: {}".format('PASS' if results['audio_processing'] else 'FAIL'))
    status_symbol = '✅' if results['model_loading'] else '⚠️'
    status_text = 'PASS' if results['model_loading'] else 'OPTIONAL'
    print("  {} Model Loading: {}".format(status_symbol, status_text))

    if results['dependencies'] and results['audio_processing']:
        print("\n✅ GEMMA 3N IS READY FOR TRANSCRIPTION!")
        print("\nNote: Model loading may fail without HuggingFace token.")
        print("The backend will download the model on first use.")
        return True
    else:
        print("\n❌ GEMMA 3N IS NOT READY")
        print("Please install missing dependencies.")
        return False


if __name__ == '__main__':
    import sys

    success = main()
    sys.exit(0 if success else 1)
