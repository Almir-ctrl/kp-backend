"""
Enhanced Audio Analysis Module (Librosa-focused)
Advanced chroma features and audio analysis using Librosa with comprehensive feature extraction
"""

import numpy as np
import librosa
from scipy.stats import pearsonr

# Optional heavy imports: scikit-learn, matplotlib, Essentia
try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
except Exception:
    PCA = None
    StandardScaler = None
    KMeans = None
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None
    # matplotlib optional for analysis plotting only
import warnings

warnings.filterwarnings('ignore')

# Essentia (optional). If not installed, Essentia-dependent functions will skip.
try:
    import essentia.standard as es
except Exception:
    es = None


class EnhancedChromaAnalyzer:
    """
    Advanced chroma feature extraction using Librosa with comprehensive analysis
    """

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512,
                 n_fft: int = 2048):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = n_fft

        # Note names for interpretation
        self.note_names = [
            'C', 'C#', 'D', 'D#', 'E', 'F',
            'F#', 'G', 'G#', 'A', 'A#', 'B'
        ]

        # Major and minor key templates
        self.major_template = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
        self.minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file with error handling"""
        try:
            # Load with librosa for compatibility
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            return y, sr
        except Exception as e:
            raise ValueError(f"Error loading audio file {file_path}: {str(e)}")

    def extract_comprehensive_chroma_features(self, y: np.ndarray) -> Dict[str, Any]:
        """Extract enhanced chroma features using Librosa"""

        # Standard chroma features
        chroma_stft = librosa.feature.chroma_stft(
            y=y, sr=self.sample_rate, hop_length=self.hop_length, n_fft=self.n_fft
        )

        # CQT-based chroma (higher frequency resolution)
        chroma_cqt = librosa.feature.chroma_cqt(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )

        # CENS chroma (Enhanced and Normalized)
        chroma_cens = librosa.feature.chroma_cens(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )

        # Harmonic-percussive separation enhanced chroma
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        chroma_harmonic = librosa.feature.chroma_stft(
            y=y_harmonic, sr=self.sample_rate, hop_length=self.hop_length
        )

        # Tuning-corrected chroma
        tuning = librosa.estimate_tuning(y=y, sr=self.sample_rate)
        chroma_tuned = librosa.feature.chroma_stft(
            y=y, sr=self.sample_rate, hop_length=self.hop_length, tuning=tuning
        )

        try:
            # Try to get tempo and beat frames
            tempo, beats = librosa.beat.beat_track(y=y, sr=self.sample_rate)
            tempo_value = tempo
            beat_frames = beats
        except Exception as e:
            # Fallback if beat tracking fails
            print(f"Warning: beat tracking failed: {e}")
            tempo_value = 0.0
            beat_frames = np.array([])

        return {
            'chroma_stft': chroma_stft,
            'chroma_cqt': chroma_cqt,
            'chroma_cens': chroma_cens,
            'chroma_harmonic': chroma_harmonic,
            'chroma_tuned': chroma_tuned,
            'tuning': tuning,
            'tempo': tempo_value,
            'beat_frames': beat_frames.tolist() if isinstance(beat_frames, np.ndarray) else []
        }

    def extract_essentia_features(self, file_path: str) -> Dict[str, Any]:
        """Extract audio features using Essentia"""
        # If Essentia is not available, return safe defaults so caller can
        # proceed with Librosa-only analysis.
        if es is None:
            return {
                'key': None,
                'scale': None,
                'key_strength': 0.0,
                'tempo': 0.0,
                'tempo_confidence': 0.0,
                'hpcp': np.array([]),
                'spectral_features': [],
                'duration': 0.0,
            }

        # When Essentia is installed, attempt a guarded extraction.
        try:
            # Use Essentia MonoLoader to load audio at the expected sample rate
            loader = es.MonoLoader(filename=file_path, sampleRate=self.sample_rate)
            audio = loader()

            # Key extraction
            key_extractor = es.KeyExtractor()
            key, scale, key_strength = key_extractor(audio)

            # Tempo extraction (guarded - different versions of Essentia may
            # expose different interfaces; use RhythmExtractor2013 if present)
            try:
                rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
                tempo, _, _, _, confidence = rhythm_extractor(audio)
            except Exception:
                tempo = 0.0
                confidence = 0.0

            # Compute HPCP (Harmonic Pitch Class Profile) per frame
            frame_size = 2048
            hop_size = 1024
            hpcp_values = []
            spectral_features = []

            try:
                for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size):
                    try:
                        windowed = es.Windowing(size=frame_size)(frame)
                        spectrum = es.Spectrum()(windowed)
                        peaks_freq, peaks_mag = es.SpectralPeaks()(spectrum)
                        if len(peaks_freq) > 0:
                            hpcp_frame = es.HPCP()(peaks_freq, peaks_mag)
                            hpcp_values.append(hpcp_frame)

                            spectral_features.append({
                                'spectral_centroid': float(es.Centroid()(spectrum)),
                                'spectral_rolloff': float(es.RollOff()(spectrum)),
                                'spectral_flux': float(es.Flux()(spectrum)),
                            })
                    except Exception:
                        # Ignore problematic frames but continue
                        continue
            except Exception:
                # If FrameGenerator or downstream calls fail, fall back to
                # empty HPCP matrix
                hpcp_values = []

            hpcp_matrix = np.array(hpcp_values).T if hpcp_values else np.array([])

            duration_val = (
                float(len(audio) / self.sample_rate)
                if hasattr(audio, '__len__')
                else 0.0
            )

            return {
                'key': key,
                'scale': scale,
                'key_strength': float(key_strength) if key_strength is not None else 0.0,
                'tempo': float(tempo),
                'tempo_confidence': float(confidence),
                'hpcp': hpcp_matrix,
                'spectral_features': spectral_features,
                'duration': duration_val,
            }
        except Exception:
            # Any failure in Essentia extraction should not crash the whole
            # analysis pipeline; return defaults instead.
            return {
                'key': None,
                'scale': None,
                'key_strength': 0.0,
                'tempo': 0.0,
                'tempo_confidence': 0.0,
                'hpcp': np.array([]),
                'spectral_features': [],
                'duration': 0.0,
            }

    def compute_advanced_chroma_statistics(self, chroma_features: Dict[str, Any]) -> Dict[str, Any]:
        """Compute advanced statistics from chroma features"""

        stats = {}

        for feature_name, chroma_matrix in chroma_features.items():
            if isinstance(chroma_matrix, np.ndarray) and chroma_matrix.ndim == 2:
                # Basic statistics
                stats[f'{feature_name}_mean'] = np.mean(chroma_matrix, axis=1).tolist()
                stats[f'{feature_name}_std'] = np.std(chroma_matrix, axis=1).tolist()
                stats[f'{feature_name}_median'] = np.median(chroma_matrix, axis=1).tolist()

                # Harmonic change detection
                chroma_diff = np.diff(chroma_matrix, axis=1)
                stats[f'{feature_name}_change_rate'] = np.mean(np.abs(chroma_diff), axis=1).tolist()

                # Key stability (how consistent the chroma distribution is)
                correlations = []
                for i in range(chroma_matrix.shape[1] - 1):
                    corr, _ = pearsonr(chroma_matrix[:, i], chroma_matrix[:, i + 1])
                    if not np.isnan(corr):
                        correlations.append(corr)

                stats[f'{feature_name}_stability'] = np.mean(correlations) if correlations else 0.0

                # Dominant pitch classes
                mean_chroma = np.mean(chroma_matrix, axis=1)
                stats[f'{feature_name}_dominant_classes'] = np.argsort(mean_chroma)[-3:].tolist()

        return stats

    def analyze_harmonic_progression(
        self,
        chroma_matrix: np.ndarray,
        beat_frames: np.ndarray,
    ) -> Dict[str, Any]:
        """Analyze harmonic progression and chord changes"""
        # Defensive checks: chroma must be a 2D array (12 x frames)
        if not isinstance(chroma_matrix, np.ndarray) or chroma_matrix.size == 0:
            return {'chord_changes': [], 'progression_complexity': 0.0}

        # Ensure beat_frames is a numpy array of frame indices
        if not isinstance(beat_frames, np.ndarray):
            try:
                beat_frames = np.array(beat_frames)
            except Exception:
                return {'chord_changes': [], 'progression_complexity': 0.0}

        if beat_frames.size < 2:
            return {'chord_changes': [], 'progression_complexity': 0.0}

        # Align chroma to beat positions. In Librosa, beat_frames are frame
        # indices aligned to feature frames, so we can use them directly.
        beat_chroma_list: List[np.ndarray] = []
        for i in range(len(beat_frames) - 1):
            start_frame = int(beat_frames[i])
            end_frame = int(beat_frames[i + 1])

            # Guard bounds and require at least one frame in the range
            if (
                start_frame < chroma_matrix.shape[1]
                and end_frame <= chroma_matrix.shape[1]
                and end_frame > start_frame
            ):
                beat_chroma_list.append(
                    np.mean(chroma_matrix[:, start_frame:end_frame], axis=1)
                )
            elif start_frame < chroma_matrix.shape[1]:
                # Fallback: single-frame representative
                beat_chroma_list.append(chroma_matrix[:, start_frame])

        beat_chroma = np.array(beat_chroma_list).T if beat_chroma_list else np.array([])

        # Detect chord changes using cosine similarity between consecutive
        # beat chroma vectors.
        chord_changes: List[Dict[str, Any]] = []
        if beat_chroma.size > 0 and beat_chroma.shape[1] > 1:
            for i in range(beat_chroma.shape[1] - 1):
                a = beat_chroma[:, i]
                b = beat_chroma[:, i + 1]
                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)
                if norm_a == 0 or norm_b == 0:
                    similarity = 1.0
                else:
                    similarity = float(np.dot(a, b) / (norm_a * norm_b))

                # If similarity is below threshold, treat as a chord change
                if similarity < 0.7:
                    if i + 1 < len(beat_frames):
                        change_time = float(beat_frames[i + 1] / self.sample_rate)
                    else:
                        change_time = 0.0

                    chord_changes.append(
                        {
                            'beat': i + 1,
                            'time': change_time,
                            'similarity': similarity,
                        }
                    )

        # Calculate progression complexity as ratio of changes to beat intervals
        if beat_frames.size > 1:
            beats_count = max(len(beat_frames) - 1, 1)
            complexity = len(chord_changes) / beats_count
        else:
            complexity = 0.0

        return {
            'chord_changes': chord_changes,
            'progression_complexity': float(complexity),
            'beat_chroma': beat_chroma.tolist() if beat_chroma.size > 0 else [],
        }

    def combine_librosa_essentia_features(
        self,
        librosa_features: Dict,
        essentia_features: Dict,
    ) -> Dict[str, Any]:
        """Combine and correlate features from both libraries"""
        combined = {'librosa': librosa_features, 'essentia': essentia_features}

        # Cross-correlate chroma features when both are available
        chroma_stft = librosa_features.get('chroma_stft')
        hpcp = essentia_features.get('hpcp')

        if (
            isinstance(chroma_stft, np.ndarray)
            and chroma_stft.size > 0
            and isinstance(hpcp, np.ndarray)
            and hpcp.size > 0
        ):
            # Resize to match the shorter dimension (frames)
            min_frames = min(chroma_stft.shape[1], hpcp.shape[1])
            if min_frames > 0:
                chroma_resized = chroma_stft[:, :min_frames]
                hpcp_resized = hpcp[:, :min_frames]

                correlations: List[float] = []
                for pitch in range(min(12, chroma_resized.shape[0])):
                    try:
                        corr, _ = pearsonr(chroma_resized[pitch], hpcp_resized[pitch])
                        if not np.isnan(corr):
                            correlations.append(float(corr))
                    except Exception:
                        continue

                chroma_hpcp_corr = float(np.mean(correlations)) if correlations else 0.0
                combined['cross_correlation'] = {
                    'chroma_hpcp_correlation': chroma_hpcp_corr,
                    'correlations_per_class': correlations,
                }

        # Compare tempo estimates if present
        librosa_tempo = float(librosa_features.get('tempo', 0) or 0)
        essentia_tempo = float(essentia_features.get('tempo', 0) or 0)
        if librosa_tempo > 0 and essentia_tempo > 0:
            tempo_diff = abs(librosa_tempo - essentia_tempo)
            tempo_agreement = 1.0 - (tempo_diff / max(librosa_tempo, essentia_tempo))
            combined['tempo_analysis'] = {
                'librosa_tempo': librosa_tempo,
                'essentia_tempo': essentia_tempo,
                'tempo_difference': float(tempo_diff),
                'tempo_agreement': float(tempo_agreement),
            }

        return combined

    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """Complete audio analysis combining Librosa and Essentia"""

        try:
            # Load audio
            y, sr = self.load_audio(file_path)

            # Extract Librosa features
            librosa_features = self.extract_librosa_chroma_features(y)

            # Extract Essentia features
            essentia_features = self.extract_essentia_features(file_path)

            # Compute advanced statistics
            chroma_stats = self.compute_advanced_chroma_statistics({
                'chroma_stft': librosa_features['chroma_stft'],
                'chroma_cqt': librosa_features['chroma_cqt'],
                'chroma_cens': librosa_features['chroma_cens'],
                'chroma_harmonic': librosa_features['chroma_harmonic'],
                'chroma_tuned': librosa_features['chroma_tuned']
            })

            # Analyze harmonic progression
            harmonic_analysis = self.analyze_harmonic_progression(
                librosa_features['chroma_stft'],
                librosa_features['beat_frames']
            )

            # Combine all features
            combined_features = self.combine_librosa_essentia_features(
                librosa_features, essentia_features
            )

            return {
                'file_path': str(file_path),
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'audio_info': {
                    'duration': float(len(y) / sr),
                    'sample_rate': sr,
                    'channels': 1
                },
                'chroma_statistics': chroma_stats,
                'harmonic_analysis': harmonic_analysis,
                'combined_features': combined_features,
                'success': True
            }

        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'success': False
            }

    def save_analysis_results(self, results: Dict[str, Any], output_path: str):
        """Save analysis results to JSON file"""

        # Convert numpy arrays to lists for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        serializable_results = convert_numpy(results)

        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)


def batch_analyze_audio_files(
    input_dir: str,
    output_dir: str,
    file_extensions: List[str] = None,
) -> List[Dict[str, Any]]:
    """Batch analyze audio files in a directory"""

    if file_extensions is None:
        file_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    analyzer = EnhancedChromaAnalyzer()
    results = []

    for ext in file_extensions:
        for audio_file in input_path.glob(f'*{ext}'):
            print(f"Analyzing: {audio_file}")

            # Analyze audio
            analysis_result = analyzer.analyze_audio_file(str(audio_file))
            results.append(analysis_result)

            # Save individual result
            output_file = output_path / f"{audio_file.stem}_analysis.json"
            analyzer.save_analysis_results(analysis_result, str(output_file))

    # Save batch summary
    summary_file = output_path / "batch_analysis_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'total_files': len(results),
            'successful_analyses': sum(1 for r in results if r.get('success', False)),
            'failed_analyses': sum(1 for r in results if not r.get('success', False)),
            'analysis_timestamp': pd.Timestamp.now().isoformat(),
            'results': results
        }, f, indent=2)

    return results


if __name__ == "__main__":
    # Example usage
    analyzer = EnhancedChromaAnalyzer()

    # Test with a sample file (replace with actual file path)
    test_file = "test_audio.wav"
    if Path(test_file).exists():
        results = analyzer.analyze_audio_file(test_file)
        analyzer.save_analysis_results(results, "test_analysis.json")
        print("Analysis complete! Results saved to test_analysis.json")
    else:
        print(f"Test file {test_file} not found. Please provide a valid audio file path.")
