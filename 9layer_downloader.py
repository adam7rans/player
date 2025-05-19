#!/usr/bin/env python3
import sys
from yt_dlp import YoutubeDL

def download_video(url, audio_only=False, format=None, download_path=None):
    # Convert YouTube Music URLs to standard YouTube format
    if 'music.youtube.com' in url:
        url = url.replace('music.youtube.com', 'www.youtube.com')
    
    # Configure yt-dlp options
    ydl_opts = {
        'progress_hooks': [progress_hook],
        'ignoreerrors': True,  # Continue on errors for playlists
        'extract_flat': False,
    }
    
    # Set output template with download path if specified
    outtmpl = '%(playlist_title)s/%(title)s.%(ext)s'
    if download_path:
        outtmpl = f'{download_path}/{outtmpl}'
    else:
        outtmpl = f'/Volumes/3ool0ne 2TB/coding tools/youtube-dl/music/{outtmpl}'
    
    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': outtmpl,
        })
    else:
        if format:
            ydl_opts.update({
                'format': format,
                'outtmpl': outtmpl,
            })
        else:
            ydl_opts.update({
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b/worst',
                'merge_output_format': 'mp4',
                'outtmpl': outtmpl,
            })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info or 'entries' in info and not info['entries']:
                print("\nError: No formats available for this video")
                return
            ydl.download([url])
        print("\nDownload completed successfully!")
    except Exception as e:
        print(f"\nError downloading video: {str(e)}")

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', '0 B/s')
        print(f"\rDownloading... {percent} at {speed}", end='')
    elif d['status'] == 'finished':
        print("\nDownload finished, now processing...")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python youtube_downloader.py \"[youtube url]\" [--audio-only] [--format <format>] [--path <download_path>]")
        sys.exit(1)
    
    url = sys.argv[1]
    audio_only = '--audio-only' in sys.argv
    format = next((arg[9:] for arg in sys.argv if arg.startswith('--format ')), None)
    download_path = next((arg[7:] for arg in sys.argv if arg.startswith('--path ')), None)
    download_video(url, audio_only, format, download_path)