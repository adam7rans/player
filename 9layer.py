#!/usr/bin/env python3
import os
import random
import subprocess
import sys
import time
import threading
from queue import Queue, Empty
from pathlib import Path
import termios
import collections # For deque

# Cassette animation frames (simplified)
CASSETTE_FRAMES = [
    "╭───────╮\n│▒▒▒▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒ ▒▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒ ▒▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒ ▒▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒▒ ▒ │\n╰───────╯",
    "╭───────╮\n│▒▒▒▒▒  │\n╰───────╯"
]

SUPPORTED_FORMATS = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac')
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = str(SCRIPT_DIR / 'music')
PLAYER_CMD = 'mpg123'

class MusicPlayer:
    def __init__(self):
        self.music_files = []
        self.current_index = 0
        self.playback_process = None
        self.running = False
        self.command_queue = Queue()
        self.random_mode = True
        self.volume = 50
        self.muted = False
        self._term_settings = None
        self.auto_play = True
        self.song_start_time = 0
        self.song_duration = 0
        self.elapsed_time = 0
        self.progress = 0
        # Initialize play_history as a deque with a max length (e.g., 50)
        self.play_history = collections.deque(maxlen=50)

    def find_music_files(self):
        files = []
        if not Path(MUSIC_DIR).is_dir():
            print(f"ERROR: Music directory does not exist: {MUSIC_DIR}")
            return files
        for root, _, filenames in os.walk(MUSIC_DIR):
            for f in filenames:
                if f.lower().endswith(SUPPORTED_FORMATS):
                    files.append(os.path.join(root, f))
        return files

    def get_song_duration(self, file_path):
        try:
            cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'"
            duration = float(subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL))
            return int(duration)
        except Exception:
            return 0

    def format_time(self, seconds):
        return f"{seconds//60}:{seconds%60:02d}"

    def get_progress_bar(self, progress, width=60):
        filled = min(int(round(width * progress)), width)
        return f"{'=' * filled}\033[38;5;236m{'-' * (width - filled)}\033[0m"

    def play_current_song(self, start_time_sec=0, played_from_history=False):
        if not self.music_files:
            return

        if self.playback_process:
            self.playback_process.terminate()
            try:
                self.playback_process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.playback_process.kill()
            self.playback_process = None

        if not played_from_history:
            if not self.play_history or self.play_history[-1] != self.current_index:
                self.play_history.append(self.current_index)

        full_song_path = self.music_files[self.current_index]
        album = os.path.basename(os.path.dirname(full_song_path))
        song_dir = os.path.dirname(full_song_path)
        song_filename = os.path.basename(full_song_path)

        if self.song_duration == 0 or start_time_sec == 0:
            self.song_duration = self.get_song_duration(full_song_path)

        self.song_start_time = time.time() - start_time_sec
        self.elapsed_time = start_time_sec

        print("\033[2J\033[H", end="")
        print("\033[0;0HNow Playing ...")
        print(f"\033[1;0H{song_filename}")
        print("\033[2;0Hfrom")
        print(f"\033[3;0H{album}")

        def animate():
            frame_idx = 0
            while self.running and self.playback_process and self.playback_process.poll() is None:
                frame = CASSETTE_FRAMES[frame_idx % len(CASSETTE_FRAMES)]
                for i, line in enumerate(frame.split('\n')):
                    print(f"\033[{5+i};0H{line}")

                self.elapsed_time = int(time.time() - self.song_start_time)
                progress = min(self.elapsed_time / self.song_duration, 1.0) if self.song_duration > 0 else 0

                time_display = f"{self.format_time(self.elapsed_time)} / {self.format_time(self.song_duration)}"
                print(f"\033[8;0H\033[K{time_display}")

                progress_bar = self.get_progress_bar(progress)
                print(f"\033[9;0H\033[K{progress_bar}")

                print(f"\033[11;0H\033[KRandom: {'ON' if self.random_mode else 'OFF'} | Volume: {'🔇 MUTED' if self.muted else '🔊 '+str(self.volume)+'%'} | AutoPlay: {'ON' if self.auto_play else 'OFF'}")
                print(f"\033[12;0H\033[KControls: [N]ext [P]rev [,]SkipBack [.]SkipNext [R]andom [A]utoPlay [=]Vol+ [-]Vol- [M]ute [Q]uit")

                time.sleep(0.1)
                frame_idx += 1

        cmd = [PLAYER_CMD, '-q']
        if start_time_sec > 0:
            frames_to_skip = int(start_time_sec * 38.28) # Approx frames for MP3
            if frames_to_skip > 0:
                cmd.extend(['-k', str(frames_to_skip)])
        cmd.append(song_filename)

        try:
            self.playback_process = subprocess.Popen(
                cmd,
                cwd=song_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            print(f"ERROR: PLAYER_CMD '{PLAYER_CMD}' not found. Is it installed and in your PATH?")
            self.running = False
            return
        except Exception as e:
            print(f"ERROR: Failed to start playback process: {e}")
            self.running = False
            return

        anim_thread = threading.Thread(target=animate)
        anim_thread.daemon = True
        anim_thread.start()

    def set_volume(self, change=None, mute=None):
        if sys.platform != 'darwin': # macOS specific volume control
            if change is not None or mute is not None:
                pass # Silently ignore on other platforms or provide a generic message
            return

        if mute is not None:
            self.muted = mute

        if change:
            self.volume = max(0, min(100, self.volume + change))
            self.muted = False # Unmute if volume is changed

        vol_to_set = 0 if self.muted else self.volume
        try:
            subprocess.run(['osascript', '-e', f"set volume output volume {vol_to_set}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError:
            pass # Silently ignore if osascript fails
        except FileNotFoundError:
            pass # Silently ignore if osascript is not found

    def stop(self):
        self.running = False
        if self.playback_process:
            self.playback_process.terminate()
            try:
                self.playback_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.playback_process.kill()
            self.playback_process = None
        if self._term_settings and sys.stdin.isatty(): # Check isatty before restoring
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._term_settings)

    def refresh_ui_stopped(self):
        """Refreshes the UI status lines when the player is stopped."""
        print(f"\033[8;0H\033[K--:-- / {self.format_time(self.song_duration) if self.song_duration > 0 else '--:--'}")
        print(f"\033[9;0H\033[K{self.get_progress_bar(0)}")
        print(f"\033[11;0H\033[KRandom: {'ON' if self.random_mode else 'OFF'} | Volume: {'🔇 MUTED' if self.muted else '🔊 '+str(self.volume)+'%'} | AutoPlay: {'ON' if self.auto_play else 'OFF'}")
        print(f"\033[12;0H\033[KControls: [N]ext [P]rev [,]SkipBack [.]SkipNext [R]andom [A]utoPlay [=]Vol+ [-]Vol- [M]ute [Q]uit")

    def player_loop(self):
        self.running = True

        input_thread = threading.Thread(target=self.input_handler)
        input_thread.daemon = True
        input_thread.start()

        self.music_files = self.find_music_files()

        if not self.music_files:
            print("No music files found in 'music' directory. Exiting.")
            self.stop()
            return

        if self.random_mode and self.music_files:
             self.current_index = random.randint(0, len(self.music_files) - 1)
        else:
            self.current_index = 0
        
        if self.auto_play and self.music_files:
            self.play_current_song()
        elif not self.music_files:
             pass

        try:
            while self.running:
                if self.playback_process and self.playback_process.poll() is not None:
                    self.playback_process = None
                    if self.auto_play and self.running:
                        self.command_queue.put('next')
                    elif not self.auto_play:
                         self.refresh_ui_stopped()

                try:
                    cmd_from_queue = self.command_queue.get(timeout=0.1)
                except Empty:
                    continue

                if cmd_from_queue == 'stop':
                    self.running = False
                    break
                elif cmd_from_queue == 'next':
                    if not self.music_files: continue
                    if self.random_mode:
                        if len(self.music_files) > 1:
                            prev_song_idx = self.current_index
                            next_idx = prev_song_idx
                            attempts = 0
                            # Try to pick a different song, limit attempts
                            while next_idx == prev_song_idx and attempts < len(self.music_files) * 2 :
                                next_idx = random.randint(0, len(self.music_files) - 1)
                                attempts += 1
                            self.current_index = next_idx
                        # If only one song, current_index doesn't change
                    else: # Sequential mode
                        self.current_index = (self.current_index + 1) % len(self.music_files)
                    self.song_duration = 0 # Reset duration for new song
                    self.play_current_song() # played_from_history defaults to False

                elif cmd_from_queue == 'prev':
                    if not self.music_files: continue
                    
                    if len(self.play_history) >= 2:
                        self.play_history.pop() # Remove current song's index
                        self.current_index = self.play_history[-1] # Get previous from history
                        self.song_duration = 0
                        self.play_current_song(played_from_history=True)
                    else:
                        # Fallback to sequential previous if history is too short
                        self.current_index = (self.current_index - 1 + len(self.music_files)) % len(self.music_files)
                        self.song_duration = 0
                        self.play_history.clear() # Clear history as we're breaking the chain
                        self.play_current_song() # played_from_history defaults to False

                elif cmd_from_queue == 'random':
                    self.random_mode = not self.random_mode
                elif cmd_from_queue == 'vol_up':
                    self.set_volume(change=10)
                elif cmd_from_queue == 'vol_down':
                    self.set_volume(change=-10)
                elif cmd_from_queue == 'mute':
                    self.set_volume(mute=not self.muted)
                elif cmd_from_queue == 'autoplay':
                    self.auto_play = not self.auto_play
                elif cmd_from_queue == 'skip_backward':
                    self.skip_backward()
                elif cmd_from_queue == 'skip_forward':
                    self.skip_forward()
                
                # Refresh UI if a command was processed that doesn't start a song, and no song is playing
                if self.playback_process is None and cmd_from_queue not in ['next', 'prev', 'skip_backward', 'skip_forward', 'stop']:
                    self.refresh_ui_stopped()
        finally:
            self.stop()

    def skip_backward(self):
        if not self.music_files: return
        if not self.playback_process: # If not playing, start current song from beginning
            self.song_duration = 0
            self.play_current_song(start_time_sec=0)
            return

        new_position = self.elapsed_time - 15
        new_position = max(0, new_position)
        # This call will use played_from_history=False by default.
        # Seeking within a song will add it to history if it wasn't the last item.
        self.play_current_song(start_time_sec=new_position)

    def skip_forward(self):
        if not self.music_files: return
        if not self.playback_process: # If not playing, act like 'next'
            self.command_queue.put('next')
            return

        new_position = self.elapsed_time + 15

        if self.song_duration > 0 and new_position >= self.song_duration - 2: # If near end, skip to next
            self.command_queue.put('next')
        elif self.song_duration == 0 and new_position > 15: # If duration unknown and skipped significantly
             self.command_queue.put('next')
        else:
            if self.song_duration > 0 :
                new_position = min(new_position, self.song_duration -1) # Cap at song end
            new_position = max(0, new_position) # Ensure not negative
            self.play_current_song(start_time_sec=new_position)

    def input_handler(self):
        import tty # Specific to this function for TTY manipulation
        fd = sys.stdin.fileno()
        if not sys.stdin.isatty(): # Check if running in a TTY
            # print("Warning: Not running in a TTY. Input handling may be limited.")
            return # Essential TTY features needed

        try:
            self._term_settings = termios.tcgetattr(fd)
        except termios.error:
            # print(f"Warning: Could not get terminal settings: {e}")
            return # Cannot proceed without terminal settings

        try:
            tty.setraw(fd)
            while self.running:
                try:
                    ch = sys.stdin.read(1)
                    if not self.running: break # Exit if player stopped

                    if ch == 'q': self.command_queue.put('stop'); break
                    elif ch == 'n': self.command_queue.put('next')
                    elif ch == 'p': self.command_queue.put('prev')
                    elif ch == ',': self.command_queue.put('skip_backward')
                    elif ch == '.': self.command_queue.put('skip_forward')
                    elif ch == 'r': self.command_queue.put('random')
                    elif ch == '=' or ch == '+': self.command_queue.put('vol_up') # Support + too
                    elif ch == '-': self.command_queue.put('vol_down')
                    elif ch == 'm': self.command_queue.put('mute')
                    elif ch == 'a': self.command_queue.put('autoplay')
                except Exception: # Catch potential errors during read
                    break 
        except Exception: # Catch potential errors during tty.setraw
            pass
        finally:
            if self._term_settings: # Restore terminal settings if they were captured
                termios.tcsetattr(fd, termios.TCSADRAIN, self._term_settings)

    def run(self):
        # Hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

        print("Scanning music directory...") # Initial message

        player_thread = threading.Thread(target=self.player_loop)
        player_thread.daemon = False # Ensure thread is joined for proper cleanup
        player_thread.start()

        try:
            player_thread.join() # Wait for the player_loop to complete
        except KeyboardInterrupt:
            print("\nStopping player...") # User interrupted
            self.command_queue.put('stop') # Signal player_loop to stop
            if player_thread.is_alive():
                player_thread.join(timeout=2) # Wait for graceful shutdown
        finally:
            # Ensure stop is called, which also restores terminal and cursor
            if self.running: # If stop wasn't called through normal flow (e.g. error in thread)
                self.stop() # This also handles restoring terminal settings

            sys.stdout.write("\033[?25h") # Show cursor
            sys.stdout.flush()
            # print("\033[2J\033[H", end="") # Optional: clear screen on exit
            print("Player stopped. Bye!")


if __name__ == "__main__":
    if not sys.stdin.isatty():
        print("This application needs to be run in a terminal for full functionality.")
        # sys.exit(1) # Optionally exit if not a TTY

    player = MusicPlayer()
    try:
        player.run()
    except Exception as e:
        # Attempt to restore terminal settings and cursor in case of an unhandled crash
        if hasattr(player, '_term_settings') and player._term_settings and sys.stdin.isatty():
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, player._term_settings)
        sys.stdout.write("\033[?25h") # Ensure cursor is visible
        sys.stdout.flush()
        # print("\033[2J\033[H", end="") # Clear screen
        print(f"An unexpected error occurred: {e}")
    # The finally block in player.run() should handle final cleanup in most cases.