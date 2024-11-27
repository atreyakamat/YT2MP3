import os
import re
import time
from pathlib import Path
from typing import Optional
from tqdm import tqdm

# Handle import errors gracefully
try:
    from pytube import YouTube
    from moviepy.editor import VideoFileClip
    import validators
except ImportError as e:
    print(f"Required module not found: {e}")
    print("Please install required modules using:")
    print("pip install pytube moviepy validators tqdm")
    exit(1)

class YouTubeDownloader:
    def __init__(self, output_path: str = 'saved'):
        """Initialize the downloader with output path"""
        self.output_path = Path(output_path)
        self.temp_path = self.output_path / 'temp'
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        self.output_path.mkdir(exist_ok=True)
        self.temp_path.mkdir(exist_ok=True)

    @staticmethod
    def _sanitize_filename(title: str) -> str:
        """Remove invalid characters from filename"""
        return re.sub(r'[<>:"/\\|?*]', '', title)

    def _get_unique_filename(self, filepath: Path) -> Path:
        """Generate unique filename if file already exists"""
        if not filepath.exists():
            return filepath

        base = filepath.stem
        extension = filepath.suffix
        counter = 1
        
        while True:
            new_filepath = filepath.parent / f"{base}_{counter}{extension}"
            if not new_filepath.exists():
                return new_filepath
            counter += 1

    def _initialize_youtube(self, url: str, max_retries: int = 3) -> Optional[YouTube]:
        """Initialize YouTube object with retry mechanism"""
        for attempt in range(max_retries):
            try:
                yt = YouTube(url)
                time.sleep(3)  # Avoid rate limiting
                
                # Test if we can access the title
                if yt.title:
                    return yt
                    
            except Exception as e:
                print(f"\nAttempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 3
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                
        return None

    def download_and_convert(self, url: str, quality: str = 'highest') -> Optional[Path]:
        """
        Download YouTube video and convert to MP3
        Args:
            url: YouTube video URL
            quality: 'highest' or 'lowest' for video quality selection
        Returns:
            Path to the converted MP3 file or None if failed
        """
        try:
            # Validate URL
            if not validators.url(url) or 'youtube.com' not in url:
                raise ValueError("Invalid YouTube URL")

            # Extract video ID and create default title
            video_id = url.split('watch?v=')[1].split('&')[0]
            default_title = f"youtube_video_{video_id}"

            # Initialize YouTube object
            yt = self._initialize_youtube(url)
            if not yt:
                raise Exception("Failed to initialize YouTube object")

            # Set up progress tracking
            progress_bar = None
            def progress_callback(stream, chunk, bytes_remaining):
                if progress_bar:
                    progress_bar.update(len(chunk))

            yt.register_on_progress_callback(progress_callback)
            yt.register_on_complete_callback(lambda stream, file_path: print("\nDownload completed!"))

            # Get video title and prepare paths
            video_title = self._sanitize_filename(yt.title or default_title)
            print(f"\nPreparing to download: {video_title}")

            # Select video stream
            stream_filter = yt.streams.filter(progressive=True, file_extension='mp4')
            video = (stream_filter.order_by('resolution').first() if quality == 'lowest' 
                    else stream_filter.order_by('resolution').desc().first())

            if not video:
                raise Exception("No suitable video stream found")

            # Download with progress bar
            progress_bar = tqdm(total=video.filesize, unit='B', unit_scale=True, desc="Downloading")
            video_path = video.download(self.temp_path)
            progress_bar.close()

            # Convert to MP3
            print("\nConverting to MP3...")
            audio_path = self._get_unique_filename(self.output_path / f"{video_title}.mp3")

            with VideoFileClip(video_path) as video_clip:
                video_clip.audio.write_audiofile(str(audio_path), logger=None)

            # Cleanup
            Path(video_path).unlink()  # Remove temporary video file
            print(f"\nSuccessfully converted to MP3: {audio_path}")
            return audio_path

        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            return None
        finally:
            # Ensure temp directory is cleaned up
            if self.temp_path.exists():
                try:
                    for file in self.temp_path.iterdir():
                        file.unlink()
                    self.temp_path.rmdir()
                except Exception:
                    pass

def main():
    downloader = YouTubeDownloader()
    
    while True:
        url = input("\nEnter YouTube URL (or 'q' to quit): ").strip()
        if url.lower() == 'q':
            break
            
        quality = input("Select quality (highest/lowest) [default: highest]: ").lower().strip()
        if quality not in ['highest', 'lowest']:
            quality = 'highest'
            
        downloader.download_and_convert(url, quality=quality)

if __name__ == "__main__":
    main() 