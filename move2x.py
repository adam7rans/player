import subprocess
import json
import sys

def get_video_framerate(file_path):
    try:
        # Run ffprobe command to get video information in JSON format
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'v:0',
            file_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        video_info = json.loads(result.stdout)
        
        # Check if 'streams' key exists in the output
        if 'streams' not in video_info:
            print(f"Error: 'streams' key not found in ffprobe output. Full output: {video_info}")
            return None
        
        # Extract the framerate
        stream = video_info['streams'][0]
        if 'avg_frame_rate' in stream:
            framerate_str = stream['avg_frame_rate']
            num, den = map(int, framerate_str.split('/'))
            framerate = num / den if den != 0 else 0
            return framerate
        else:
            print(f"Error: 'avg_frame_rate' not found in stream information. Stream info: {stream}")
            return None
    
    except subprocess.CalledProcessError as e:
        print(f"Error running ffprobe: {e}")
        print(f"ffprobe stderr output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        print(f"Raw ffprobe output: {result.stdout}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def decrease_framerate(input_file, output_file, target_fps=None):
    try:
        # Use exactly 30 fps for best compatibility
        if target_fps is None:
            target_fps = "30"
            
        command = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'libx264',     # H264 video codec
            '-c:a', 'aac',         # AAC audio codec
            '-b:a', '128k',        # Standard audio bitrate
            '-filter_complex',
            # Use fps filter with interpolation for smoother frame conversion
            f'[0:v]minterpolate=\'mi_mode=mci:mc_mode=aobmc:fps={target_fps}\',fps={target_fps}[v];[0:a]aresample=async=1[a]',
            '-map', '[v]',         # Map video stream
            '-map', '[a]',         # Map audio stream
            '-movflags', '+faststart',  # Enable fast start for streaming
            output_file
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Successfully converted {input_file} to {target_fps} fps.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting video: {e}")
        print(f"ffmpeg stderr output: {e.stderr}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python move2x.py <path_to_mov_file>")
        sys.exit(1)
    
    mov_file = sys.argv[1]
    framerate = get_video_framerate(mov_file)
    
    if framerate is not None:
        print(f"The framerate of {mov_file} is {framerate:.2f} fps")
        
        if framerate > 60:
            print("Warning: Frame rate exceeds maximum allowed 60 fps")
            user_input = input("Do you want to convert to 30 fps? (y/n): ").lower()
            if user_input == 'y':
                output_file = mov_file.rsplit('.', 1)[0] + '_30fps.mp4'
                if decrease_framerate(mov_file, output_file):
                    print(f"Converted file saved as {output_file}")
                else:
                    print("Conversion failed.")
        elif framerate < 30:
            print(f"Frame rate is below 30 fps. Will interpolate frames to reach 30 fps.")
            output_file = mov_file.rsplit('.', 1)[0] + '_30fps.mp4'
            if decrease_framerate(mov_file, output_file):
                print(f"Converted file saved as {output_file}")
            else:
                print("Conversion failed.")
        elif framerate != 30:
            user_input = input("Do you want to convert to 30 fps for optimal compatibility? (y/n): ").lower()
            if user_input == 'y':
                output_file = mov_file.rsplit('.', 1)[0] + '_30fps.mp4'
                if decrease_framerate(mov_file, output_file):
                    print(f"Converted file saved as {output_file}")
                else:
                    print("Conversion failed.")
        else:
            print("The framerate is already 30 fps. No conversion needed.")
    else:
        print(f"Failed to determine the framerate of {mov_file}")
