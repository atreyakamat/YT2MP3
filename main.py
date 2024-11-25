try:
    from pytube import YouTube
    from moviepy import VideoFileClip
    from tqdm import tqdm
    import os
    import re
    import validators
    import time
except ImportError as e:
    print(f"Required module not found: {e}")
    print("Please install required modules using:")
    print("pip install pytube moviepy validators tqdm")
    exit(1)

def sanitize_filename(title):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', title)

def get_unique_filename(filepath):
    """Generate unique filename if file already exists"""
    base, extension = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{extension}"
        counter += 1
    return filepath

def download_and_convert(url, output_path='saved', quality='highest'):
    """
    Download YouTube video and convert to MP3
    quality: 'highest' or 'lowest' for video quality selection
    """
    try:
        # Validate URL
        if not validators.url(url) or 'youtube.com' not in url:
            raise ValueError("Invalid YouTube URL")

        # Extract video ID from URL
        video_id = url.split('watch?v=')[1].split('&')[0]
        default_title = f"youtube_video_{video_id}"
        
        # Initialize YouTube object with retry mechanism
        max_retries = 3
        video_title = default_title
        yt = None
        
        for attempt in range(max_retries):
            try:
                # Simplified YouTube initialization
                yt = YouTube(url)
                # Add a longer sleep to avoid rate limiting
                time.sleep(3)
                
                if hasattr(yt, 'title') and yt.title:
                    video_title = yt.title
                    break
                    
            except Exception as e:
                if "HTTP Error 403" in str(e):
                    print(f"\nAttempt {attempt + 1}/{max_retries} failed: YouTube API access denied. Retrying...")
                else:
                    print(f"\nAttempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 3  # Increased wait time
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                continue
        
        if not yt:
            raise Exception("Failed to initialize YouTube object")

        # Now add the callbacks
        progress_bar = None  # Define progress_bar in broader scope
        def progress_callback(stream, chunk, bytes_remaining):
            if progress_bar:
                progress_bar.update(len(chunk))
        
        yt.register_on_progress_callback(progress_callback)
        yt.register_on_complete_callback(lambda stream, file_path: print("\nDownload completed!"))

        # Sanitize the video title for filename
        video_title = sanitize_filename(video_title)
        print(f"\nPreparing to download: {video_title}")

        # Create temp directory
        temp_path = os.path.join(output_path, 'temp')
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        # Select video stream based on quality preference
        if quality == 'lowest':
            video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').first()
        else:  # highest
            video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

        # Calculate file size and initialize progress bar
        filesize = video.filesize
        progress_bar = tqdm(total=filesize, unit='B', unit_scale=True, desc="Downloading")

        # Download the video
        video_path = video.download(temp_path)
        progress_bar.close()

        print("\nConverting to MP3...")
        # Generate unique filename for output
        audio_path = os.path.join(output_path, f"{video_title}.mp3")
        audio_path = get_unique_filename(audio_path)

        # Convert to MP3 with progress bar
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path, logger=None)  # logger=None to avoid duplicate progress output
        
        # Clean up
        video_clip.close()
        os.remove(video_path)
        os.rmdir(temp_path)
        
        print(f"\nSuccessfully converted to MP3: {audio_path}")
        return audio_path
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    while True:
        url = input("\nEnter YouTube URL (or 'q' to quit): ")
        if url.lower() == 'q':
            break
            
        quality = input("Select quality (highest/lowest) [default: highest]: ").lower()
        if quality not in ['highest', 'lowest']:
            quality = 'highest'
            
        download_and_convert(url, quality=quality) 