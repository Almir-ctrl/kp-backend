"""
YouTube Download Service for AiMusicSeparator Backend
Handles YouTube video/audio downloads with format conversion
"""
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, Literal, Any

# Quality presets for different formats
QUALITY_PRESETS = {
    'high': {
        'mp3': '320',
        'wav': '0',  # lossless
        'flac': '0',  # lossless
        'mp4': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    },
    'medium': {
        'mp3': '192',
        'wav': '0',
        'flac': '5',  # compression level
        'mp4': 'bestvideo[height<=720]+bestaudio/best[height<=720]'
    },
    'low': {
        'mp3': '128',
        'wav': '0',
        'flac': '8',
        'mp4': 'bestvideo[height<=480]+bestaudio/best[height<=480]'
    }
}


class YouTubeDownloader:
    """Handle YouTube downloads with yt-dlp"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename"""
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    def _get_yt_dlp_command(
        self,
        url: str,
        format_type: Literal['mp3', 'wav', 'flac', 'mp4'],
        quality: Literal['high', 'medium', 'low']
    ) -> list:
        """Build yt-dlp command with format and quality options, always set a modern user-agent"""
        output_template = str(self.output_dir / '%(title)s.%(ext)s')
        # Modern Chrome user-agent (2025)
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        base_cmd = [
            'yt-dlp',
            url,
            '--no-playlist',
            '--output', output_template,
            '--no-warnings',
            '--no-check-certificate',
            '--user-agent', user_agent,
        ]
        if format_type == 'mp3':
            bitrate = QUALITY_PRESETS[quality]['mp3']
            base_cmd.extend([
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', bitrate,
                '--embed-thumbnail',
                '--add-metadata',
            ])
        elif format_type == 'wav':
            base_cmd.extend([
                '--extract-audio',
                '--audio-format', 'wav',
                '--audio-quality', '0',
            ])
        elif format_type == 'flac':
            compression = QUALITY_PRESETS[quality]['flac']
            base_cmd.extend([
                '--extract-audio',
                '--audio-format', 'flac',
                '--audio-quality', compression,
                '--embed-thumbnail',
                '--add-metadata',
            ])
        elif format_type == 'mp4':
            format_string = QUALITY_PRESETS[quality]['mp4']
            base_cmd.extend([
                '--format', format_string,
                '--merge-output-format', 'mp4',
                '--embed-thumbnail',
                '--add-metadata',
            ])
        return base_cmd

    def download(
        self,
        url: str,
        format_type: Literal['mp3', 'wav', 'flac', 'mp4'] = 'mp3',
        quality: Literal['high', 'medium', 'low'] = 'high'
    ) -> Dict[str, Any]:
        """
        Download YouTube video/audio

        Returns:
            Dict with 'success', 'title', 'filename', 'path', 'error' keys
        """
        try:
            # First, get video info (with user-agent)
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
            info_cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--user-agent', user_agent,
                url
            ]
            info_result = subprocess.run(
                info_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if info_result.returncode != 0:
                # Special handling for 403 errors
                if (
                    '403' in info_result.stderr or
                    'Forbidden' in info_result.stderr
                ):
                    return {
                        'success': False,
                        'error': (
                            'YouTube is blocking the download (HTTP 403 Forbidden). '
                            'Update yt-dlp or try a different video.'
                        )
                    }
                return {
                    'success': False,
                    'error': (
                        f'Failed to fetch video info: {info_result.stderr}'
                    )
                }
            video_info = json.loads(info_result.stdout)
            title = self._sanitize_filename(video_info.get('title', 'Unknown'))
            # Build download command
            download_cmd = self._get_yt_dlp_command(url, format_type, quality)
            # Execute download
            result = subprocess.run(
                download_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max
            )
            if result.returncode != 0:
                # Special handling for 403 errors
                if (
                    '403' in result.stderr or
                    'Forbidden' in result.stderr
                ):
                    return {
                        'success': False,
                        'error': (
                            'YouTube is blocking the download (HTTP 403 Forbidden). '
                            'Update yt-dlp or try a different video.'
                        )
                    }
                return {
                    'success': False,
                    'error': f'Download failed: {result.stderr}'
                }
            # Find the downloaded file
            expected_filename = f"{title}.{format_type}"
            file_path = self.output_dir / expected_filename
            if not file_path.exists():
                # Try to find any recently created file
                files = list(self.output_dir.glob(f"{title}*"))
                if files:
                    file_path = max(files, key=lambda p: p.stat().st_mtime)
                else:
                    return {
                        'success': False,
                        'error': 'Downloaded file not found'
                    }
            result_dict = {
                'success': True,
                'title': title,
                'filename': file_path.name,
                'path': str(file_path),
                'format': format_type,
            }
            try:
                result_dict['quality'] = quality
                result_dict['size_mb'] = round(file_path.stat().st_size / (1024 * 1024), 2)
            except Exception:
                # best-effort, not critical
                pass
            return result_dict

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Download timed out (max 10 minutes)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video metadata without downloading"""
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr
                }

            info = json.loads(result.stdout)

            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'description': info.get('description', '')[:500]
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
