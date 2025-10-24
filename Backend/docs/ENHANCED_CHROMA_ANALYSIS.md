# 🎵 Enhanced Chroma Analysis with Librosa

## Overview

I've successfully set up **Librosa's enhanced chroma features** for comprehensive music analysis in your AI Music Separator AI separator backend. The system provides advanced harmonic analysis, key detection, and temporal music structure analysis.

## 🚀 Features Implemented

### 🎼 Advanced Chroma Feature Extraction
- **Multiple Methods**: STFT, CQT, CENS, Harmonic, and Tuning-corrected chroma
- **High Resolution**: CQT-based analysis for better frequency resolution
- **Normalized Features**: CENS (Chroma Energy Normalized Statistics) for robustness

### 🎹 Musical Analysis Capabilities
- **Key Detection**: Template matching for major/minor key estimation
- **Tempo Analysis**: BPM detection with beat tracking
- **Harmonic Progression**: Chord change detection and complexity analysis
- **Spectral Features**: Centroid, rolloff, bandwidth, zero-crossing rate
- **Temporal Stability**: Frame-to-frame correlation analysis

### 📊 Advanced Statistics
- **Pitch Class Dominance**: Identification of most prominent notes
- **Harmonic Rhythm**: Measurement of chord change frequency  
- **Temporal Dynamics**: Change rate analysis across time
- **Stability Metrics**: Consistency measurements

## 🛠️ Technical Implementation

### Core Components

1. **EnhancedChromaAnalyzer Class** (`librosa_chroma_analyzer.py`)
   - Comprehensive feature extraction
   - Statistical analysis methods
   - Key and mode estimation
   - Harmonic progression analysis

2. **Flask API Endpoints**
   - `POST /analyze/chroma/<file_id>` - Single file analysis
   - `POST /analyze/batch` - Batch processing

3. **Dependencies Added**
   ```
   scipy
   matplotlib  
   scikit-learn
   pandas
   ```

### Key Methods

```python
# Main analysis function
analyzer = EnhancedChromaAnalyzer()
results = analyzer.analyze_audio_file("audio.wav")

# Key detection
key_info = analyzer.estimate_key_and_mode(chroma_matrix)

# Chord progression analysis  
harmony_info = analyzer.analyze_harmonic_progression(chroma, beats)

# Statistical analysis
stats = analyzer.compute_chroma_statistics(chroma_features)
```

## 🎯 API Usage

### 1. Single File Analysis

```bash
# Upload audio file first
curl -X POST -F "file=@song.wav" https://localhost/upload

# Analyze with enhanced chroma features
curl -X POST https://localhost/analyze/chroma/<file_id>
```

**Response Example:**
```json
{
  "file_id": "abc123",
  "analysis_type": "enhanced_chroma",
  "status": "completed",
  "key_info": {
    "detected_key": "C",
    "key_strength": 0.85,
    "scale": "major"
  },
  "tempo_info": {
    "librosa_tempo": 120.5
  },
  "harmonic_complexity": 0.23,
  "chord_changes_count": 8,
  "message": "Enhanced chroma analysis completed successfully"
}
```

### 2. Batch Analysis

```bash
curl -X POST https://localhost/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"file_ids": ["file1", "file2", "file3"]}'
```

## 🔬 Analysis Output Structure

### Audio Information
- Duration, sample rate, tuning deviation
- Tempo (BPM) and total beat count

### Key Analysis
- Detected key and mode (major/minor)
- Confidence score (0.0 - 1.0)
- Chroma profile distribution

### Harmonic Analysis  
- Chord change events with timestamps
- Progression complexity metric
- Harmonic rhythm measurements

### Chroma Statistics (per method)
- Mean, standard deviation, median
- Temporal stability scores
- Dominant pitch class identification
- Change rate analysis

### Spectral Features Summary
- Spectral centroid, rolloff, bandwidth
- Zero-crossing rate
- RMS energy levels

## 🎼 Musical Insights

### Key Detection Accuracy
- Uses template matching against major/minor scales
- Rotates templates through all 12 keys
- Returns confidence score for reliability assessment

### Chord Progression Analysis
- Detects harmonic changes using cosine similarity
- Measures progression complexity (changes per beat)
- Identifies temporal locations of chord transitions

### Harmonic vs Percussive Separation
- Separates harmonic and percussive components
- Analyzes chroma features from harmonic content only
- Reduces noise from percussion instruments

## 🚀 Performance Optimizations

### Efficient Processing
- Vectorized numpy operations
- Optimized hop lengths for real-time capability
- Caching of intermediate results

### Scalability
- Batch processing support
- Async analysis capabilities
- Resource-aware processing

## 📈 Advanced Applications

### Music Information Retrieval
- Automatic music transcription enhancement
- Chord symbol recognition
- Key signature detection

### Music Production
- Harmonic complexity analysis
- Tempo stability assessment
- Key relationship analysis for mixing

### Academic Research
- Music theory validation
- Compositional analysis
- Genre classification features

## 🔧 Configuration Options

### Analyzer Parameters
```python
analyzer = EnhancedChromaAnalyzer(
    sample_rate=22050,    # Audio sample rate
    hop_length=512,       # Analysis frame hop size
    n_fft=2048           # FFT window size
)
```

### Feature Extraction Control
- Multiple chroma extraction methods
- Configurable frequency resolution
- Tuning correction options

## 📚 Integration Examples

### With Existing Demucs Separation
```python
# 1. Separate audio with Demucs
# 2. Analyze harmonic content with enhanced chroma
# 3. Compare harmonic complexity across stems
```

### With Whisper Transcription  
```python
# 1. Transcribe lyrics with Whisper
# 2. Analyze musical harmony with chroma features
# 3. Align lyrics with chord progressions
```

## 🔬 Technical Details

### Chroma Feature Types

1. **STFT Chroma**: Standard short-time Fourier transform based
2. **CQT Chroma**: Constant-Q transform for better frequency resolution
3. **CENS Chroma**: Energy-normalized for robustness
4. **Harmonic Chroma**: From harmonic-separated audio
5. **Tuned Chroma**: Corrected for tuning deviations

### Statistical Measures

- **Temporal Stability**: Frame-to-frame correlation
- **Dominant Classes**: Most prominent pitch classes  
- **Change Rate**: Rate of harmonic progression
- **Entropy**: Measure of chroma distribution uniformity

## 🎵 Ready for Production

Your enhanced chroma analysis system is now ready with:

✅ **Librosa Integration**: Advanced music analysis capabilities  
✅ **API Endpoints**: RESTful interface for analysis requests  
✅ **Comprehensive Features**: Key detection, harmony, tempo, spectral analysis  
✅ **Batch Processing**: Efficient handling of multiple files  
✅ **Statistical Analysis**: Deep insights into musical structure  
✅ **Production Ready**: Deployed with Docker and nginx  

The system provides professional-grade music analysis capabilities suitable for music information retrieval, academic research, and commercial applications! 🎼✨