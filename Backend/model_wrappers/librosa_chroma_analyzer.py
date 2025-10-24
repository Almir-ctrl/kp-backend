"""
Enhanced Audio Analysis Module (Librosa-focused)
Advanced chroma features and comprehensive music analysis using Librosa
"""

import numpy as np
import librosa
# Optional imports (removed here to avoid F401 when unused). If needed,
# re-introduce or import in local scope where used.
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any
import warnings

warnings.filterwarnings("ignore")


class EnhancedChromaAnalyzer:
    """Advanced chroma feature extraction using Librosa"""

    def __init__(
        self,
        sample_rate: int = 22050,
        hop_length: int = 512,
        n_fft: int = 2048,
    ):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = n_fft

        # Note names for interpretation
        self.note_names = [
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

        # Key templates for major and minor scales
        self.major_template = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
        self.minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

    def load_audio(self, file_path: str) -> tuple[np.ndarray, int]:
        """Load audio file with error handling"""
        try:
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            return y, sr
        except Exception as e:
            raise ValueError(f"Error loading audio: {str(e)}")

    def extract_comprehensive_chroma_features(
        self, y: np.ndarray
    ) -> Dict[str, Any]:
        """Extract comprehensive chroma features using multiple methods"""

        # Standard STFT-based chroma
        chroma_stft = librosa.feature.chroma_stft(
            y=y,
            sr=self.sample_rate,
            hop_length=self.hop_length,
            n_fft=self.n_fft,
        )

        # CQT-based chroma (higher frequency resolution)
        chroma_cqt = librosa.feature.chroma_cqt(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )

        # CENS chroma (Enhanced and Normalized)
        chroma_cens = librosa.feature.chroma_cens(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )

        # Harmonic-percussive separation
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        chroma_harmonic = librosa.feature.chroma_stft(
            y=y_harmonic, sr=self.sample_rate, hop_length=self.hop_length
        )

        # Tuning estimation and correction
        tuning = librosa.estimate_tuning(y=y, sr=self.sample_rate)
        chroma_tuned = librosa.feature.chroma_stft(
            y=y, sr=self.sample_rate, hop_length=self.hop_length, tuning=tuning
        )

        # Tempo and beat tracking
        tempo, beats = librosa.beat.beat_track(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )

        return {
            "chroma_stft": chroma_stft,
            "chroma_cqt": chroma_cqt,
            "chroma_cens": chroma_cens,
            "chroma_harmonic": chroma_harmonic,
            "chroma_tuned": chroma_tuned,
            "tuning": float(tuning),
            "tempo": float(tempo),
            "beats": beats,
        }

    def extract_spectral_features(self, y: np.ndarray) -> Dict[str, Any]:
        """Extract additional spectral features"""

        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )[0]

        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )[0]

        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=y, sr=self.sample_rate, hop_length=self.hop_length
        )[0]

        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(
            y, hop_length=self.hop_length
        )[0]

        # MFCC features
        mfccs = librosa.feature.mfcc(
            y=y, sr=self.sample_rate, n_mfcc=13, hop_length=self.hop_length
        )

        # RMS energy
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]

        return {
            "spectral_centroids": spectral_centroids,
            "spectral_rolloff": spectral_rolloff,
            "spectral_bandwidth": spectral_bandwidth,
            "zero_crossing_rate": zcr,
            "mfccs": mfccs,
            "rms_energy": rms,
        }

    def estimate_key_and_mode(self, chroma: np.ndarray) -> Dict[str, Any]:
        """Estimate musical key and mode using template matching"""

        if chroma.size == 0:
            return {"key": "Unknown", "mode": "unknown", "confidence": 0.0}

        # Average chroma over time
        mean_chroma = np.mean(chroma, axis=1)

        # Normalize
        if np.sum(mean_chroma) > 0:
            mean_chroma = mean_chroma / np.sum(mean_chroma)

        # Template matching for all keys
        major_correlations = []
        minor_correlations = []

        for shift in range(12):
            # Shift templates for each key
            shifted_major = np.roll(self.major_template, shift)
            shifted_minor = np.roll(self.minor_template, shift)

            # Calculate correlations
            if len(mean_chroma) == len(shifted_major):
                major_corr = np.corrcoef(mean_chroma, shifted_major)[0, 1]
                minor_corr = np.corrcoef(mean_chroma, shifted_minor)[0, 1]

                major_correlations.append(
                    major_corr if not np.isnan(major_corr) else 0
                )
                minor_correlations.append(
                    minor_corr if not np.isnan(minor_corr) else 0
                )
            else:
                major_correlations.append(0)
                minor_correlations.append(0)

        # Find best matches
        best_major_idx = np.argmax(major_correlations)
        best_minor_idx = np.argmax(minor_correlations)

        best_major_corr = major_correlations[best_major_idx]
        best_minor_corr = minor_correlations[best_minor_idx]

        # Determine if major or minor
        if best_major_corr > best_minor_corr:
            estimated_key = self.note_names[best_major_idx]
            estimated_mode = "major"
            confidence = best_major_corr
        else:
            estimated_key = self.note_names[best_minor_idx]
            estimated_mode = "minor"
            confidence = best_minor_corr

        return {
            "key": estimated_key,
            "mode": estimated_mode,
            "confidence": float(confidence)
            if not np.isnan(confidence)
            else 0.0,
            "chroma_profile": mean_chroma.tolist(),
        }

    def analyze_harmonic_progression(
        self, chroma: np.ndarray, beats: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze harmonic progression and chord changes"""

        if chroma.size == 0 or len(beats) == 0:
            return {
                "chord_changes": [],
                "progression_complexity": 0.0,
                "harmonic_rhythm": 0.0,
            }

        # Convert beat times to frame indices
        beat_frames = (
            librosa.frames_to_samples(beats, hop_length=self.hop_length)
            // self.hop_length
        )

        # Ensure beat frames are within bounds
        beat_frames = beat_frames[beat_frames < chroma.shape[1]]

        if len(beat_frames) < 2:
            return {
                "chord_changes": [],
                "progression_complexity": 0.0,
                "harmonic_rhythm": 0.0,
            }

        # Extract chroma for each beat
        beat_chromas = []
        for i in range(len(beat_frames) - 1):
            start_frame = int(beat_frames[i])
            end_frame = int(beat_frames[i + 1])

            if end_frame > start_frame and end_frame <= chroma.shape[1]:
                beat_chroma = np.mean(chroma[:, start_frame:end_frame], axis=1)
                beat_chromas.append(beat_chroma)

        if len(beat_chromas) < 2:
            return {
                "chord_changes": [],
                "progression_complexity": 0.0,
                "harmonic_rhythm": 0.0,
            }

        beat_chromas = np.array(beat_chromas).T

        # Detect chord changes using cosine similarity
        chord_changes = []
        similarities = []

        for i in range(beat_chromas.shape[1] - 1):
            vec1 = beat_chromas[:, i]
            vec2 = beat_chromas[:, i + 1]

            # Calculate cosine similarity
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 > 0 and norm2 > 0:
                similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            else:
                similarity = 1.0

            similarities.append(similarity)

            # Threshold for chord change detection
            if similarity < 0.75:
                beat_time = beats[i + 1] if i + 1 < len(beats) else 0
                chord_changes.append(
                    {
                        "beat": i + 1,
                        "time": float(beat_time),
                        "similarity": float(similarity),
                    }
                )

        # Calculate metrics
        progression_complexity = len(chord_changes) / max(
            len(beat_chromas[0]) - 1, 1
        )
        harmonic_rhythm = (
            np.mean([1 - s for s in similarities]) if similarities else 0.0
        )

        return {
            "chord_changes": chord_changes,
            "progression_complexity": float(progression_complexity),
            "harmonic_rhythm": float(harmonic_rhythm),
        }

    def compute_chroma_statistics(
        self, chroma_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute statistics from chroma features"""

        stats = {}

        for feature_name, chroma_matrix in chroma_features.items():
            if (
                isinstance(chroma_matrix, np.ndarray)
                and chroma_matrix.ndim == 2
            ):
                # Basic statistics
                stats[f"{feature_name}_mean"] = np.mean(
                    chroma_matrix, axis=1
                ).tolist()
                stats[f"{feature_name}_std"] = np.std(
                    chroma_matrix, axis=1
                ).tolist()

                # Temporal stability
                correlations = []
                for i in range(chroma_matrix.shape[1] - 1):
                    corr = np.corrcoef(
                        chroma_matrix[:, i], chroma_matrix[:, i + 1]
                    )[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)

                stats[f"{feature_name}_stability"] = (
                    np.mean(correlations) if correlations else 0.0
                )

                # Dominant pitch classes
                mean_chroma = np.mean(chroma_matrix, axis=1)
                stats[f"{feature_name}_dominant_classes"] = np.argsort(
                    mean_chroma
                )[-3:].tolist()

        return stats

    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """Complete audio analysis with enhanced chroma features"""

        try:
            # Load audio
            y, sr = self.load_audio(file_path)

            # Extract chroma features
            chroma_features = self.extract_comprehensive_chroma_features(y)

            # Extract spectral features
            spectral_features = self.extract_spectral_features(y)

            # Key and mode estimation
            key_analysis = self.estimate_key_and_mode(
                chroma_features["chroma_cqt"]
            )

            # Harmonic progression analysis
            harmonic_analysis = self.analyze_harmonic_progression(
                chroma_features["chroma_cqt"], chroma_features["beats"]
            )

            # Compute statistics
            chroma_stats = self.compute_chroma_statistics(
                {
                    "chroma_stft": chroma_features["chroma_stft"],
                    "chroma_cqt": chroma_features["chroma_cqt"],
                    "chroma_cens": chroma_features["chroma_cens"],
                    "chroma_harmonic": chroma_features["chroma_harmonic"],
                    "chroma_tuned": chroma_features["chroma_tuned"],
                }
            )

            return {
                "file_path": str(file_path),
                "analysis_timestamp": pd.Timestamp.now().isoformat(),
                "audio_info": {
                    "duration": float(len(y) / sr),
                    "sample_rate": sr,
                    "tuning_deviation": chroma_features["tuning"],
                    "tempo": chroma_features["tempo"],
                    "total_beats": len(chroma_features["beats"]),
                },
                "key_analysis": key_analysis,
                "harmonic_analysis": harmonic_analysis,
                "chroma_statistics": chroma_stats,
                "spectral_summary": {
                    "spectral_centroid_mean": float(
                        np.mean(spectral_features["spectral_centroids"])
                    ),
                    "spectral_rolloff_mean": float(
                        np.mean(spectral_features["spectral_rolloff"])
                    ),
                    "spectral_bandwidth_mean": float(
                        np.mean(spectral_features["spectral_bandwidth"])
                    ),
                    "zero_crossing_rate_mean": float(
                        np.mean(spectral_features["zero_crossing_rate"])
                    ),
                    "rms_energy_mean": float(
                        np.mean(spectral_features["rms_energy"])
                    ),
                },
                "success": True,
            }

        except Exception as e:
            return {
                "file_path": str(file_path),
                "error": str(e),
                "success": False,
            }

    def save_analysis_results(self, results: Dict[str, Any], output_path: str):
        """Save analysis results to JSON file"""

        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, dict):
                return {
                    key: convert_numpy(value) for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        serializable_results = convert_numpy(results)

        with open(output_path, "w") as f:
            json.dump(serializable_results, f, indent=2)


def batch_analyze_audio_files(
    input_dir: str, output_dir: str, file_extensions: List[str] = None
) -> List[Dict[str, Any]]:
    """Batch analyze audio files in a directory"""

    if file_extensions is None:
        file_extensions = [".wav", ".mp3", ".flac", ".m4a", ".ogg"]

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    analyzer = EnhancedChromaAnalyzer()
    results = []

    for ext in file_extensions:
        for audio_file in input_path.glob(f"*{ext}"):
            print(f"Analyzing: {audio_file}")

            # Analyze audio
            analysis_result = analyzer.analyze_audio_file(str(audio_file))
            results.append(analysis_result)

            # Save individual result
            output_file = (
                output_path / f"{audio_file.stem}_enhanced_analysis.json"
            )
            analyzer.save_analysis_results(analysis_result, str(output_file))

    return results


if __name__ == "__main__":
    # Example usage
    analyzer = EnhancedChromaAnalyzer()
    print("Enhanced Chroma Analyzer ready!")
    print(
        "Features: Advanced chroma analysis, key detection, harmonic progression analysis"
    )
