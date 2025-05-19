#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time
import threading
from queue import Queue
from pathlib import Path

SUPPORTED_FORMATS = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac')
MUSIC_DIR = '/Volumes/3ool0ne 2TB/coding tools/youtube-dl/music'
PLAYER_CMD = 'afplay' if sys.platform == 'darwin' else 'mpg123'

class MusicPlayer:
    def __init__(self):
        self.music_files = []
        self.current_index = 0
        self.playback_process = None
        self.running = False
        self.command_queue = Queue()
        self.random_mode = False  # Random playback toggle
        self.volume = 50  # Default volume (0-100)
        self.muted = False
        
    def find_music_files(self):
        files = []
        for root, _, filenames in os.walk(MUSIC_DIR):
            for f in filenames:
                if f.lower().endswith(SUPPORTED_FORMATS):
                    files.append(os.path.join(root, f))
        return files
    
    def play_current_song(self):
        if not self.music_files:
            return
            
        if self.playback_process:
            self.playback_process.terminate()
            self.playback_process.wait()
            
        song = self.music_files[self.current_index]
        print(f"\n\033[1mNow playing ({self.current_index+1}/{len(self.music_files)}):\033[0m")
        print(f"{os.path.basename(song)}")
        print(f"From: {os.path.dirname(song)}")
        
        self.playback_process = subprocess.Popen([PLAYER_CMD, song])
    
    def set_volume(self, change=None, mute=None):
        """Set volume using AppleScript (macOS only)"""
        if sys.platform != 'darwin':
            print("Volume control only available on macOS")
            return
            
        if mute is not None:
            self.muted = mute
            
        if change:
            self.volume = max(0, min(100, self.volume + change))
            self.muted = False
            
        vol = 0 if self.muted else self.volume
        script = f"set volume output volume {vol}"
        subprocess.run(['osascript', '-e', script])
        print(f"\nVolume: {'🔇 MUTED' if self.muted else '🔊 '+str(self.volume)+'%'}")
    
    def player_loop(self):
        while self.running:
            if not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd == 'next':
                    if self.random_mode:
                        self.current_index = random.randint(0, len(self.music_files)-1)
                    else:
                        self.current_index = (self.current_index + 1) % len(self.music_files)
                    self.play_current_song()
                elif cmd == 'prev':
                    self.current_index = (self.current_index - 1) % len(self.music_files)
                    self.play_current_song()
                elif cmd == 'random':
                    self.random_mode = not self.random_mode
                    print(f"\nRandom mode {'ON' if self.random_mode else 'OFF'}")
                elif cmd == 'vol_up':
                    self.set_volume(change=10)
                elif cmd == 'vol_down':
                    self.set_volume(change=-10)
                elif cmd == 'mute':
                    self.set_volume(mute=not self.muted)
                elif cmd == 'stop':
                    break
            elif self.playback_process and self.playback_process.poll() is not None:
                # Song finished naturally
                if self.random_mode:
                    self.current_index = random.randint(0, len(self.music_files)-1)
                else:
                    self.current_index = (self.current_index + 1) % len(self.music_files)
                self.play_current_song()
            
            time.sleep(0.1)
    
    def input_handler(self):
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == 'n':
                    self.command_queue.put('next')
                elif cmd == 'p':
                    self.command_queue.put('prev')
                elif cmd == 'r':
                    self.command_queue.put('random')
                elif cmd == '=':
                    self.command_queue.put('vol_up')
                elif cmd == '-':
                    self.command_queue.put('vol_down')
                elif cmd == 'm':
                    self.command_queue.put('mute')
                elif cmd == 'q':
                    self.command_queue.put('stop')
                    break
            except (EOFError, KeyboardInterrupt):
                self.command_queue.put('stop')
                break
    
    def run(self):
        print("Scanning music directory...")
        self.music_files = self.find_music_files()
        
        if not self.music_files:
            print(f"No supported audio files found in {MUSIC_DIR}")
            return
        
        print(f"Found {len(self.music_files)} songs")
        self.current_index = random.randint(0, len(self.music_files)-1)
        self.running = True
        
        # Start with first song immediately
        self.play_current_song()
        self.set_volume()  # Initialize volume
        print("\nControls: [N]ext | [P]revious | [R]andom | [=]VolUp | [-]VolDown | [M]ute | [Q]uit")
        print(f"Random mode: {'ON' if self.random_mode else 'OFF'}")
        
        # Start player thread
        player_thread = threading.Thread(target=self.player_loop)
        player_thread.daemon = True
        player_thread.start()
        
        # Start input handling in main thread
        self.input_handler()
        
        # Cleanup
        self.running = False
        if self.playback_process:
            self.playback_process.terminate()
        player_thread.join()
        print("\nPlayer stopped")

if __name__ == "__main__":
    player = MusicPlayer()
    player.run()