#!/usr/bin/env python
"""Compare transcription outputs between Transformers AutoModel and
converted Whisper checkpoint.

Usage:
    python compare_transformers_vs_whisper.py --transformers-dir <path>
        --whisper-pt <path>

The script will:
 - generate a short test WAV,
 - load transformers processor+model and run transcription,
 - load converted whisper checkpoint with whisper.load_model and
     transcribe, and then
 - print both transcripts and a simple token overlap score.
"""
from pathlib import Path
import argparse
import tempfile
import sys
import time


def gen_sine_wav(path, duration=1.0, sr=16000, freq=440.0):
    import numpy as np
    import soundfile as sf

    t = np.linspace(0, duration, int(sr * duration), False)
    tone = 0.4 * np.sin(2 * np.pi * freq * t)
    sf.write(str(path), tone.astype('float32'), sr)


def gen_tts_wav(path, text: str = 'Hello world this is a quick test'):
    """Synthesize deterministic TTS using Windows SAPI via PowerShell.

    This is platform-specific (Windows). On other platforms, fallback to
    generating a sine wave (not ideal).
    """
    import subprocess
    # PowerShell command to synthesize WAV using System.Speech
    ps_cmd = (
        "Add-Type -AssemblyName System.speech;"
        " $s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f" $s.SetOutputToWaveFile('{path}');"
        " $s.Rate = 0;"
        f" $s.Speak(\"{text}\");"
        " $s.Dispose();"
    )
    try:
        subprocess.run([
            'powershell', '-NoProfile', '-Command', ps_cmd
        ], check=True)
    except Exception as e:
        print('TTS synthesis failed, falling back to sine:', e)
        gen_sine_wav(path)


def simple_token_overlap(a, b):
    ta = a.lower().split()
    tb = b.lower().split()
    if not ta or not tb:
        return 0.0
    s = set(ta) & set(tb)
    return len(s) / max(len(set(ta)), 1)


def wer(ref, hyp):
    """Compute a simple Word Error Rate (WER) between ref and hyp."""
    r = ref.lower().split()
    h = hyp.lower().split()
    # classic dynamic programming edit distance
    import numpy as np

    d = np.zeros((len(r) + 1, len(h) + 1), dtype=int)
    for i in range(len(r) + 1):
        d[i, 0] = i
    for j in range(len(h) + 1):
        d[0, j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            if r[i - 1] == h[j - 1]:
                d[i, j] = d[i - 1, j - 1]
            else:
                substitute = d[i - 1, j - 1] + 1
                insert = d[i, j - 1] + 1
                delete = d[i - 1, j] + 1
                d[i, j] = min(substitute, insert, delete)
    if len(r) == 0:
        return 1.0 if len(h) > 0 else 0.0
    return d[len(r), len(h)] / len(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--transformers-dir', required=True)
    parser.add_argument('--whisper-pt', required=True)
    parser.add_argument(
        '--language',
        help=(
            'Optional language to pass to models. Do not force a language '
            'unless you want deterministic behavior.'
        ),
    )
    parser.add_argument(
        '--tts-text',
        help='TTS text to synthesize (platform-specific)',
        default='Hello world this is a quick test',
    )
    args = parser.parse_args()

    tdir = Path(args.transformers_dir)
    wpt = Path(args.whisper_pt)
    if not tdir.exists():
        print('Transformers dir not found:', tdir)
        return 2
    if not wpt.exists():
        print('Whisper checkpoint not found:', wpt)
        return 3

    tmp = Path(tempfile.gettempdir()) / 'compare_transformers_vs_whisper.wav'
    print('Generating deterministic spoken test WAV:', tmp)
    gen_tts_wav(str(tmp), text=args.tts_text)

    # 1) Transformers transcription
    print('\nLoading Transformers model from', tdir)
    try:
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
    except Exception as e:
        print('transformers not available:', e)
        return 4
    proc = AutoProcessor.from_pretrained(str(tdir))
    tmodel = AutoModelForSpeechSeq2Seq.from_pretrained(str(tdir))
    # optionally provide generation kwargs if language/task explicitly set
    gen_kwargs = {}
    if args.language:
        gen_kwargs = {'language': args.language, 'task': 'transcribe'}
    import torch
    # read audio as numpy array and pass to processor
    import soundfile as sf
    audio_arr, sr = sf.read(str(tmp))
    data = proc(
        audio_arr, sampling_rate=sr, return_tensors='pt'
    )
    # transformers whisper processors may return 'input_features' or
    # 'input_values' depending on version; accept either
    if 'input_features' in data:
        input_values = data['input_features']
    elif 'input_values' in data:
        input_values = data['input_values']
    else:
        raise RuntimeError(
            'Processor did not return input_features or input_values'
        )
    # run inference
    t0 = time.time()
    with torch.no_grad():
        # move inputs to model device if needed
        model_device = next(tmodel.parameters()).device
        if input_values.device != model_device:
            input_values = input_values.to(model_device)
        # Transformers whisper expects input_features=... for generate
    # pass gen kwargs only if provided. Transformers will use its
    # defaults otherwise.
    generated = tmodel.generate(input_features=input_values, **gen_kwargs)
    ttrans = proc.batch_decode(generated, skip_special_tokens=True)[0]
    ttime = time.time() - t0
    print(f'Transformers transcript (time={ttime:.2f}s):')
    print('  ', ttrans)

    # 2) Whisper checkpoint transcription
    print('\nLoading converted Whisper checkpoint:', wpt)
    try:
        import whisper
    except Exception as e:
        print('whisper lib not available:', e)
        return 5

    # reuse existing loader if present
    loader_path = Path(__file__).parent / 'whisper_loader.py'
    loader = None
    if loader_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'whisper_loader', str(loader_path)
        )
        if spec is not None and spec.loader is not None:
            mod = importlib.util.module_from_spec(spec)
            # type: ignore[attr-defined]
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            loader = mod

    if loader and hasattr(loader, 'get_preferred_device'):
        device = loader.get_preferred_device()
    else:
        device = 'cpu'

    print('  preferred device:', device)
    w0 = time.time()
    # whisper.load_model accepts a path or name; we pass the full pt path
    model = whisper.load_model(str(wpt), device=device)
    wtime = time.time() - w0
    print('Loaded whisper model in', f'{wtime:.2f}s')

    w0 = time.time()
    # pass language/task only when provided by the user; don't force English
    if args.language:
        wres = model.transcribe(
            str(tmp), language=args.language, task='transcribe'
        )
    else:
        wres = model.transcribe(str(tmp))
    wtime2 = time.time() - w0
    wtrans = wres.get('text', '')
    print(f'Whisper transcript (time={wtime2:.2f}s):')
    print('  ', wtrans)

    # Compare
    overlap = simple_token_overlap(ttrans, wtrans)
    w = wer(ttrans, wtrans)
    print('\nToken overlap score (0-1):', f'{overlap:.3f}')
    print('Word Error Rate (WER):', f'{w:.3f}')
    print('\nDone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
