#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time
import threading
from queue import Queue
from pathlib import Path
import termios

# Cassette animation frames
CASSETTE_FRAMES = [
    "╭───────╮\n│ ▒▒▒▒▒ │\n│◁ ┃ ┃ ▷│\n│ ▒▒▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒▒▒▒ │\n│◁ ┃ ┃ ▷│\n│▒▒▒▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒ ▒▒▒▒ │\n│◁ ┃ ┃ ▷│\n│▒ ▒▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒ ▒▒▒ │\n│◁ ┃ ┃ ▷│\n│▒▒ ▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒ ▒▒ │\n│◁ ┃ ┃ ▷│\n│▒▒▒ ▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒▒ ▒ │\n│◁ ┃ ┃ ▷│\n│▒▒▒▒ ▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒▒▒  │\n│◁ ┃ ┃ ▷│\n│▒▒▒▒▒  │\n╰───────╯"
]

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
        self.random_mode = True  # Random playback enabled by default
        self.volume = 50  # Default volume (0-100)
        self.muted = False
        self._term_settings = None
        self.auto_play = True  # Auto-play enabled by default

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
        album = os.path.basename(os.path.dirname(song))
        
        # Clear screen and set absolute positions
        print("\033[2J\033[H", end="")  # Clear screen
        
        # Fixed positions for all elements
        print("\033[0;0HNow Playing ...")  # Top-left
        print(f"\033[1;0H{os.path.basename(song)}")
        print("\033[2;0Hfrom")
        print(f"\033[3;0H{album}")
        
        def animate():
            frame_idx = 0
            while not self.command_queue.empty() or \
                 (self.playback_process and self.playback_process.poll() is None):
                frame = CASSETTE_FRAMES[frame_idx % len(CASSETTE_FRAMES)]
                
                # Print animation at fixed position (row 5, column 0)
                for i, line in enumerate(frame.split('\n')):
                    print(f"\033[{5+i};0H{line}")
                
                # Status bar at fixed bottom position
                print(f"\033[10;0H\033[KRandom: {'ON' if self.random_mode else 'OFF'} | Volume: {'🔇 MUTED' if self.muted else '🔊 '+str(self.volume)+'%'} | AutoPlay: {'ON' if self.auto_play else 'OFF'}")
                print(f"\033[11;0H\033[KControls: [N]ext [P]rev [<]SkipBack [>]SkipNext [R]andom [A]utoPlay [=]Vol+ [-]Vol- [M]ute [Q]uit")
                
                time.sleep(0.1)
                frame_idx += 1
        
        self.playback_process = subprocess.Popen([PLAYER_CMD, song])
        anim_thread = threading.Thread(target=animate)
        anim_thread.daemon = True
        anim_thread.start()
    
    def set_volume(self, change=None, mute=None):
        """Set volume without extra output"""
        if sys.platform != 'darwin':
            return
            
        if mute is not None:
            self.muted = mute
            
        if change:
            self.volume = max(0, min(100, self.volume + change))
            self.muted = False
            
        vol = 0 if self.muted else self.volume
        subprocess.run(['osascript', '-e', f"set volume output volume {vol}"])
    
    def stop(self):
        self.running = False
        if self.playback_process:
            self.playback_process.terminate()
            try:
                self.playback_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.playback_process.kill()
        if self._term_settings:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._term_settings)

    def player_loop(self):
        self.running = True
        
        # Start input handler in separate thread
        input_thread = threading.Thread(target=self.input_handler)
        input_thread.daemon = True
        input_thread.start()
        
        # Load music files
        self.music_files = self.find_music_files()
        
        # Start playing
        if self.music_files and self.auto_play:
            self.play_current_song()
            
        while self.running:
            cmd = self.command_queue.get()
            if cmd == 'stop':
                self.running = False
            elif cmd == 'next':
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
            elif cmd == 'vol_up':
                self.set_volume(change=10)
            elif cmd == 'vol_down':
                self.set_volume(change=-10)
            elif cmd == 'mute':
                self.set_volume(mute=not self.muted)
            elif cmd == 'autoplay':
                self.auto_play = not self.auto_play
            elif cmd == 'skip_back':
                if self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process.wait()
                    self.play_current_song()
            elif cmd == 'skip_forward':
                if self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process.wait()
                    if self.random_mode:
                        self.current_index = random.randint(0, len(self.music_files)-1)
                    else:
                        self.current_index = (self.current_index + 1) % len(self.music_files)
                    self.play_current_song()
            
            # Update status display
            print(f"\033[10;0H\033[KRandom: {'ON' if self.random_mode else 'OFF'} | Volume: {'🔇 MUTED' if self.muted else '🔊 '+str(self.volume)+'%'} | AutoPlay: {'ON' if self.auto_play else 'OFF'}")
            print(f"\033[11;0H\033[KControls: [N]ext [P]rev [<]SkipBack [>]SkipNext [R]andom [A]utoPlay [=]Vol+ [-]Vol- [M]ute [Q]uit")
            
            time.sleep(0.1)
    
    def input_handler(self):
        import tty
        fd = sys.stdin.fileno()
        self._term_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while self.running:
                cmd = sys.stdin.read(1).lower()
                if cmd == 'q':
                    self.stop()
                    os._exit(0)  # Force exit the program
                    return
                elif cmd == 'n':
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
                elif cmd == 'a':
                    self.command_queue.put('autoplay')
                elif cmd == '<':
                    self.command_queue.put('skip_back')
                elif cmd == '>':
                    self.command_queue.put('skip_forward')
        except Exception as e:
            self.stop()
            raise

    def run(self):
        print("Scanning music directory...")
        self.music_files = self.find_music_files()
        
        if not self.music_files:
            print(f"\033[KNo supported audio files found in {MUSIC_DIR}")
            print("\033[KPlease download some music first using downloader.py")
            return
            
        print(f"\033[KFound {len(self.music_files)} songs")
        self.running = True
        self.current_index = random.randint(0, len(self.music_files)-1)
        
        # Start playing immediately if autoplay is enabled
        if self.auto_play:
            self.play_current_song()
        
        # Start player thread
        player_thread = threading.Thread(target=self.player_loop)
        player_thread.daemon = True
        player_thread.start()
        
        # Wait for player thread to finish
        player_thread.join()
        print("\033[KPlayer stopped")

if __name__ == "__main__":
    player = MusicPlayer()
    player.run()