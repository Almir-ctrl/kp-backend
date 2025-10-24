"""
Enhanced Progress Tracking System
Provides real-time and predictive progress updates for audio processing
"""
import time
import threading
import librosa
from flask_socketio import SocketIO


class ProgressTracker:
    """Track and emit real-time progress for audio processing stages"""

    def __init__(self, socketio: SocketIO, file_id: str):
        self.socketio = socketio
        self.file_id = file_id
        self.audio_duration = None
        self.start_times = {}

    def set_audio_duration(self, audio_path: str):
        """Calculate audio duration for time-based predictions"""
        try:
            y, sr = librosa.load(audio_path, sr=None, duration=1)
            # Get full duration without loading entire file
            import soundfile as sf
            info = sf.info(audio_path)
            self.audio_duration = info.duration
            print(f"Audio duration: {self.audio_duration:.2f} seconds")
        except Exception as e:
            print(f"Could not determine audio duration: {e}")
            self.audio_duration = 180  # Default to 3 minutes

    def emit_progress(
        self,
        stage: str,
        progress: float,
        message: str = "",
        estimated_time: float = None,
    ):
        """Emit progress update via WebSocket"""
        data = {
            'file_id': self.file_id,
            'stage': stage,
            'progress': min(100, max(0, progress)),
            'message': message
        }

        if estimated_time is not None:
            data['estimated_time'] = estimated_time

        self.socketio.emit('processing_progress', data)

    def start_upload_progress(self, total_size: int):
        """Track real-time upload progress"""
        self.start_times['upload'] = time.time()
        self.emit_progress('upload', 0, f'Uploading file ({total_size / (1024*1024):.1f} MB)...')

    def update_upload_progress(self, bytes_uploaded: int, total_size: int):
        """Update upload progress based on bytes transferred"""
        progress = (bytes_uploaded / total_size) * 100
        mb_uploaded = bytes_uploaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)

        elapsed = time.time() - self.start_times.get('upload', time.time())
        if elapsed > 0 and bytes_uploaded > 0:
            speed = (bytes_uploaded / elapsed) / (1024 * 1024)  # MB/s
            remaining_bytes = total_size - bytes_uploaded
            eta = remaining_bytes / (speed * 1024 * 1024) if speed > 0 else 0

            self.emit_progress(
                'upload',
                progress,
                f'Uploading: {mb_uploaded:.1f}/{mb_total:.1f} MB ({speed:.1f} MB/s)',
                eta
            )
        else:
            self.emit_progress(
                'upload',
                progress,
                f'Uploading: {mb_uploaded:.1f}/{mb_total:.1f} MB',
            )

    def complete_upload(self):
        """Mark upload as complete"""
        elapsed = time.time() - self.start_times.get('upload', time.time())
        self.emit_progress('upload', 100, f'Upload complete ({elapsed:.1f}s)')

    def start_separation_progress(self):
        """Start tracking separation with time-based prediction"""
        self.start_times['separation'] = time.time()

        # Estimate separation time based on audio duration
        # Demucs typically takes 0.5-2x audio duration on CPU
        estimated_time = self.audio_duration * 1.5 if self.audio_duration else 180

        self.emit_progress(
            'separation',
            0,
            'Initializing audio separation...',
            estimated_time
        )

        # Start predictive progress thread
        self._start_predictive_progress('separation', estimated_time)

    def update_separation_progress(self, progress: float, message: str = ''):
        """Update separation progress (if processor provides it)"""
        elapsed = time.time() - self.start_times.get('separation', time.time())
        self.emit_progress(
            'separation',
            progress,
            message or f'Separating audio... ({elapsed:.0f}s)',
        )

    def complete_separation(self):
        """Mark separation as complete"""
        elapsed = time.time() - self.start_times.get('separation', time.time())
        self.emit_progress('separation', 100, f'Separation complete ({elapsed:.1f}s)')

    def start_transcription_progress(self):
        """Start tracking transcription with prediction"""
        self.start_times['transcription'] = time.time()

        # Estimate transcription time:
        # - Model loading: ~5 seconds (first time: ~30s)
        # - Feature extraction: ~2-5 seconds
        # - Generation: ~10-30 seconds
        estimated_time = 20 + (self.audio_duration * 0.5) if self.audio_duration else 45

        self.emit_progress(
            'transcription',
            0,
            'Loading AI model...',
            estimated_time
        )

        # Start predictive progress thread
        self._start_predictive_progress('transcription', estimated_time)

    def update_transcription_progress(self, progress: float, message: str = ''):
        """Update transcription progress"""
        elapsed = time.time() - self.start_times.get('transcription', time.time())
        self.emit_progress(
            'transcription',
            progress,
            message or f'Transcribing... ({elapsed:.0f}s)',
        )

    def complete_transcription(self):
        """Mark transcription as complete"""
        elapsed = time.time() - self.start_times.get('transcription', time.time())
        self.emit_progress('transcription', 100, f'Transcription complete ({elapsed:.1f}s)')

    def start_karaoke_progress(self):
        """Start tracking karaoke generation"""
        self.start_times['karaoke'] = time.time()

        # Karaoke is fast: ~5-10 seconds
        estimated_time = 10 + (self.audio_duration * 0.05) if self.audio_duration else 15

        self.emit_progress(
            'karaoke',
            0,
            'Syncing lyrics with audio...',
            estimated_time
        )

        # Start predictive progress thread
        self._start_predictive_progress('karaoke', estimated_time)

    def update_karaoke_progress(self, progress: float, message: str = ''):
        """Update karaoke progress"""
        elapsed = time.time() - self.start_times.get('karaoke', time.time())
        self.emit_progress(
            'karaoke',
            progress,
            message or f'Generating karaoke... ({elapsed:.0f}s)',
        )

    def complete_karaoke(self):
        """Mark karaoke as complete"""
        elapsed = time.time() - self.start_times.get('karaoke', time.time())
        self.emit_progress('karaoke', 100, f'Karaoke complete ({elapsed:.1f}s)')

    def complete_all(self):
        """Mark entire pipeline as complete"""
        total_elapsed = time.time() - self.start_times.get('upload', time.time())
        self.socketio.emit('processing_progress', {
            'file_id': self.file_id,
            'stage': 'complete',
            'progress': 100,
            'message': f'All processing complete! ({total_elapsed:.1f}s total)',
            'total_time': total_elapsed
        })

    def emit_error(self, stage: str, error_message: str):
        """Emit error for a stage"""
        self.socketio.emit('processing_progress', {
            'file_id': self.file_id,
            'stage': stage,
            'progress': 0,
            'message': f'Error: {error_message}',
            'error': error_message
        })

    def _start_predictive_progress(self, stage: str, estimated_time: float):
        """
        Start a thread that updates progress predictively based on time
        Uses sigmoid curve for realistic progress feel
        """
        def update_progress():
            start = time.time()
            last_progress = 0

            while True:
                elapsed = time.time() - start

                # Use sigmoid curve for realistic progress
                # Fast start, slow middle, fast end
                if elapsed >= estimated_time:
                    break

                # Sigmoid function: progress = 1 / (1 + e^(-k*(t - t0)))
                # Adjusted to never quite reach 100% until actual completion
                t_normalized = (elapsed / estimated_time) * 12 - 6  # Scale to sigmoid range
                progress = 95 / (1 + 2.718 ** (-t_normalized))  # Max 95% predictively

                # Only emit if progress increased significantly
                if progress - last_progress >= 1:
                    elapsed_str = f"{int(elapsed)}s"
                    remaining = estimated_time - elapsed
                    remaining_str = f"{int(remaining)}s remaining"

                    message = f"{stage.capitalize()}... {elapsed_str} elapsed, ~{remaining_str}"
                    self.emit_progress(stage, progress, message, remaining)
                    last_progress = progress

                time.sleep(0.5)  # Update every 500ms

        # Start prediction thread
        thread = threading.Thread(target=update_progress, daemon=True)
        thread.start()


def create_progress_tracker(socketio: SocketIO, file_id: str) -> ProgressTracker:
    """Factory function to create a progress tracker"""
    return ProgressTracker(socketio, file_id)
