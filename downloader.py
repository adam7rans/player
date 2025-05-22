#!/usr/bin/env python3
import sys
import sqlite3
from pathlib import Path
import os
from yt_dlp import YoutubeDL

# Database setup
DB_PATH = Path(__file__).parent / 'music_metadata.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Albums/Playlists table (combined)
        conn.execute('''CREATE TABLE IF NOT EXISTS albums
                     (id TEXT PRIMARY KEY,
                      title TEXT,
                      artist TEXT,
                      type TEXT CHECK(type IN ('album', 'playlist')),
                      url TEXT)''')
        
        # Tracks table
        conn.execute('''CREATE TABLE IF NOT EXISTS tracks
                     (id TEXT PRIMARY KEY,
                      title TEXT,
                      album_id TEXT,
                      position INTEGER,
                      url TEXT,
                      file_path TEXT,
                      download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY(album_id) REFERENCES albums(id))''')
        
        # Optional artists table
        conn.execute('''CREATE TABLE IF NOT EXISTS artists
                     (name TEXT PRIMARY KEY,
                      description TEXT)''')
        conn.commit()

init_db()

def store_metadata(info, file_path):
    with sqlite3.connect(DB_PATH) as conn:
        # Determine if this is a playlist or album
        is_playlist = 'playlist_id' in info
        album_id = info['playlist_id'] if is_playlist else f"manual_{info['id']}"
        
        # Insert album/playlist
        conn.execute('''INSERT OR IGNORE INTO albums
                     (id, title, artist, type, url)
                     VALUES (?, ?, ?, ?, ?)''',
                     (album_id,
                      info.get('playlist_title') if is_playlist else info.get('album', 'Unknown Album'),
                      info.get('artist'),
                      'playlist' if is_playlist else 'album',
                      info.get('webpage_url')))
        
        # Insert track
        conn.execute('''INSERT OR REPLACE INTO tracks
                     (id, title, album_id, position, url, file_path)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                     (info['id'],
                      info.get('title'),
                      album_id,
                      info.get('playlist_index', 1) if is_playlist else info.get('track_number', 1),
                      info.get('webpage_url'),
                      file_path))
        
        # Optional: Store artist separately
        if artist := info.get('artist'):
            conn.execute('''INSERT OR IGNORE INTO artists (name) VALUES (?)''', (artist,))
        
        conn.commit()

def download_video(url, audio_only=False, format=None, download_path=None):
    # Convert YouTube Music URLs to standard YouTube format
    if 'music.youtube.com' in url:
        url = url.replace('music.youtube.com', 'www.youtube.com')
    
    # Configure yt-dlp options
    ydl_opts = {
        'progress_hooks': [progress_hook],
        'ignoreerrors': True,
        'extract_flat': False,
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
            {'key': 'FFmpegMetadata'}
        ]
    }
    
    # Set output template
    outtmpl = '%(artist)s/%(album)s/%(title)s.%(ext)s'
    if download_path:
        outtmpl = f'{download_path}/{outtmpl}'
    else:
        print("Debug: Using default music path with playlist/album folders")
        outtmpl = str(Path(os.path.dirname(os.path.abspath(__file__))) / 'music' / outtmpl)
    
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
            ydl_opts['format'] = format
        else:
            ydl_opts['format'] = 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b/worst'
        ydl_opts['outtmpl'] = outtmpl

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Store metadata for each track
            if 'entries' in info:  # Playlist
                for entry in info['entries']:
                    if entry:
                        store_metadata(entry, ydl.prepare_filename(entry))
            else:  # Single track
                store_metadata(info, ydl.prepare_filename(info))
            
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

def is_playlist_downloaded(playlist_id):
    """Check if a playlist is already fully downloaded"""
    with sqlite3.connect(DB_PATH) as conn:
        # Check if playlist exists in albums table
        playlist_exists = conn.execute(
            "SELECT 1 FROM albums WHERE id = ? AND type = 'playlist'",
            (playlist_id,)
        ).fetchone()
        
        if not playlist_exists:
            return False
            
        # Check if all tracks are downloaded
        track_count = conn.execute(
            """SELECT COUNT(*) FROM tracks t
               JOIN albums a ON t.album_id = a.id
               WHERE a.id = ?""",
            (playlist_id,)
        ).fetchone()[0]
        
        # Get expected track count from YouTube
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/playlist?list={playlist_id}",
                download=False
            )
            expected_count = len(info['entries']) if 'entries' in info else 0
        
        return track_count >= expected_count

def download_missing_playlists(playlist_urls):
    """Download only missing playlists from a list"""
    for url in playlist_urls:
        playlist_id = url.split('list=')[1]
        if not is_playlist_downloaded(playlist_id):
            print(f"Downloading missing playlist: {playlist_id}")
            download_video(url, audio_only=True)
        else:
            print(f"Playlist {playlist_id} already downloaded")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python youtube_downloader.py \"[youtube url]\" [--audio-only] [--format <format>] [--path <download_path>]")
        sys.exit(1)
    
    url = sys.argv[1]
    audio_only = '--audio-only' in sys.argv
    format = None
    download_path = None
    
    # Properly parse all arguments
    for i, arg in enumerate(sys.argv[2:]):
        if arg.startswith('--format='):
            format = arg.split('=')[1]
        elif arg.startswith('--path='):
            download_path = arg.split('=')[1]
        elif arg == '--format' and i+2 < len(sys.argv):
            format = sys.argv[i+3]
        elif arg == '--path' and i+2 < len(sys.argv):
            download_path = sys.argv[i+3]
    
    print(f"Final parsed arguments - audio_only: {audio_only}, format: {format}, download_path: {download_path}")
    download_video(url, audio_only, format, download_path)