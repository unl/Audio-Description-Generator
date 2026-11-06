""" FFMPEG helper functions for running common commands """
import os
import argparse
import subprocess

VIDEO_ENCODING = 'libx264'
ENCODER_PRESET = 'fast'
CONSTANT_RATE_FACTOR = '23'
PIXEL_FORMAT = 'yuv420p'
FRAME_RATE = '30'

AUDIO_ENCODING = 'aac'
BITRATE = '192k'
SAMPLE_RATE = '48000'
AUDIO_CHANNELS = '2'

STILL_FRAME_AUDIO_PADDING_SECONDS = '0.5'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_FOLDER = os.path.join(SCRIPT_DIR, 'tmp')

DEBUG = False

def set_video_encoding(new_encoding:str):
    """ Sets VIDEO_ENCODING """

    # pylint: disable=global-statement
    global VIDEO_ENCODING
    VIDEO_ENCODING = new_encoding

def set_debug(new_debug:bool):
    """ Sets DEBUG """

    # pylint: disable=global-statement
    global VIDEO_ENCODING
    VIDEO_ENCODING = new_debug

def timecode_to_seconds(timecode: str) -> float:
    """ Convert a timecode string (hh:mm:ss.ms) to total seconds as a float """
    hours, minutes, seconds = timecode.split(":")
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return total_seconds

def seconds_to_timecode(seconds: float) -> str:
    """Convert total seconds as a float to a timecode string (hh:mm:ss.ms)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60  # keep fractional part

    # Format with 2-digit hours/minutes and 2 decimal places for seconds
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

def frame_to_timecode(video_input: str, frame_number: int) -> str:
    """ Converts a frame number to hh:mm:ss.ms timecode for a given video """
    fps = get_framerate(video_input)

    # Convert frame number to seconds
    seconds = frame_number / fps

    # Convert seconds to timecode string
    return seconds_to_timecode(seconds)

def video_to_audio_wav(video_input:str, audio_output:str):
    """ Converts a video file to the audio wav file """
    cmd = [
        'ffmpeg', '-y', '-i', video_input,
        '-ac', '1', '-ar', '16000',
        audio_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def slow_down_audio_file(audio_input:str, audio_output:str, slow_down_percent:float = 0.8):
    """ Slow down audio file by specified percentage"""
    cmd = [
        'ffmpeg', '-y',
        '-i', audio_input,
        '-filter:a', f'atempo={slow_down_percent}',
        audio_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def get_duration(media_input:str) -> float:
    """ Converts a video file to the audio wav file """
    cmd = [
        'ffprobe', '-i', media_input,
        '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout)

def get_framerate(video_input: str) -> int:
    """ Get video FPS using ffprobe """
    fps_cmd = [
        'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=nokey=1:noprint_wrappers=1',
        video_input
    ]
    fps_result = subprocess.run(fps_cmd, capture_output=True, text=True, check=True)
    num, denom = map(int, fps_result.stdout.strip().split('/'))
    fps = num / denom

    return fps

def get_total_frames(video_input: str) -> int:
    """
    Returns the total number of frames in a video using ffprobe.
    """
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-select_streams', 'v:0',
        '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0',
        video_input
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout)


def normalize_video(video_input:str, video_output:str):
    """ Taking the input video and normalizing it to standard video parameters """
    cmd = [
        'ffmpeg', '-y', '-i', video_input,
        # Video settings
        '-c:v', VIDEO_ENCODING, '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        # Audio settings
        '-c:a', AUDIO_ENCODING, '-b:a', BITRATE, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        video_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def cut_video_into_clip(video_input:str, video_output:str, start_time:str, end_time:str):
    """ Based on the start time and end time it will cut the video and save a copy """
    # Re-encode the clip to avoid issues when it comes to key frames
    cmd = [
        'ffmpeg', '-y',
        # Video input
        '-i', video_input,
        # Seek to start time and cut to end time
        '-ss', start_time, '-to', end_time,
        '-avoid_negative_ts', 'make_zero', '-fflags', '+genpts',
        # Video settings
        '-c:v', VIDEO_ENCODING, '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        # Audio settings
        '-c:a', AUDIO_ENCODING, '-b:a', BITRATE, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        video_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def save_first_frame_as_image(video_input:str, image_output:str):
    """ Saves the first frame from a video file and saves the image"""
    cmd = [
        'ffmpeg', '-y', '-i', video_input, '-frames:v', '1', '-pix_fmt', PIXEL_FORMAT, '-update', '1',
        image_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def save_frame_at_time_as_image(video_input:str, seconds:float, image_output:str, image_scale:int=0):
    """ Saves the first frame from a video file and saves the image """
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(seconds),
        '-i', video_input,
        '-frames:v', '1']

    if image_scale > 0:
        cmd.extend(['-vf', f'scale={image_scale}:-1'])

    cmd.extend([
        '-update', '1',
        image_output
    ])

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def save_frame_by_number(video_input:str, frame_number:int, output_image:str, image_scale:int=0):
    """ Save a specific frame by frame number using ffmpeg """
    # Convert frame number to timecode
    timecode = frame_to_timecode(video_input, frame_number)

    cmd = ['ffmpeg', '-v', 'quiet', '-y', '-i', video_input, '-ss', timecode, '-frames:v', '1']

    if image_scale > 0:
        cmd.extend(['-vf', f'scale={image_scale}:{-1}'])

    cmd.append(output_image)
    subprocess.run(cmd, check=True)

def create_still_frame_narration_clip(audio_input:str, image_input:str, video_output:str):
    """ Using the image and audio file it will create a still frame video (with a bit of silence at the end of the clip) """
    cmd = [
        'ffmpeg', '-y',
        # Loop image for the whole video
        '-loop', '1', '-i', image_input,
        # Add narration track
        '-i', audio_input,
        # Video settings
        '-c:v', VIDEO_ENCODING, '-tune', 'stillimage', '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        # Audio settings
        '-c:a', AUDIO_ENCODING, '-b:a', BITRATE, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        # Make sure the output matches the shortest stream length
        # This argument `-max_interleave_delta 100M` is there to prevent any weird silence at the end of the video
        '-shortest', '-max_interleave_delta', '100M',
        video_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def export_clips_to_file(clips_file_output:str, clips: list):
    """ Taking a list of clips (file paths) it will write it to a file for ffmpeg """
    with open(clips_file_output, 'w', encoding='utf-8') as clips_file:
        for clip in clips:
            clips_file.write(f'file {clip.replace(f'{TMP_FOLDER}/', "")}\n')

def combine_videos(video_output:str, clips_file_input: str):
    """ Taking a clips file it will concat all the videos together """
    cmd = [
        'ffmpeg', '-y',
        # Concat videos into one video clip
        '-f', 'concat', '-safe', '0', '-i', clips_file_input,
        # We will re-encode the concatenated video so include the video and audio settings
        '-c:v', VIDEO_ENCODING, '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        '-c:a', AUDIO_ENCODING, '-b:a', BITRATE, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        video_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

# -------------------------------
# CLI Entry
# -------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Detect audio blocks from audio input')
    parser.add_argument('-f',
                        '--function',
                        required=True,
                        help='Function you wish to run')
    parser.add_argument('-v',
                        '--video',
                        default=None,
                        help='Video file path input')
    parser.add_argument('-a',
                        '--audio',
                        default=None,
                        help='Audio file path input')
    parser.add_argument('-i',
                        '--image',
                        default=None,
                        help='Image file path input')
    parser.add_argument('-t',
                        '--text',
                        default=None,
                        help='Text file path input')
    parser.add_argument('-st',
                        '--start_time',
                        default=None,
                        help='Start time in timecode format')
    parser.add_argument('-et',
                        '--end_time',
                        default=None,
                        help='End time in timecode format')
    parser.add_argument('-td',
                        '--time_duration',
                        default=None,
                        help='Time in seconds')
    parser.add_argument('-o',
                        '--output',
                        default=None,
                        help='Output file path')
    args = parser.parse_args()

    if args.function == 'video_to_audio_wav':
        if args.video is None:
            raise ValueError('Missing video input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        video_to_audio_wav(args.video, args.output)

    elif args.function == 'get_duration':
        if args.video is not None:
            print(get_duration(args.video))
        elif args.audio is not None:
            print(get_duration(args.audio))
        raise ValueError('Missing video input file path or audio input path')

    elif args.function == 'normalize_video':
        if args.video is None:
            raise ValueError('Missing video input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        normalize_video(args.video, args.output)

    elif args.function == 'cut_video_into_clip':
        if args.video is None:
            raise ValueError('Missing video input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        if args.start_time is None:
            raise ValueError('Missing start timecode')
        if args.end_time is None:
            raise ValueError('Missing end timecode')
        cut_video_into_clip(args.video, args.output, args.start_time, args.end_time)

    elif args.function == 'save_first_frame_as_image':
        if args.video is None:
            raise ValueError('Missing video input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        save_first_frame_as_image(args.video, args.output)

    elif args.function == 'save_frame_at_time_as_image':
        if args.video is None:
            raise ValueError('Missing video input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        if args.time_duration is None:
            raise ValueError('Missing time duration in seconds')
        save_frame_at_time_as_image(args.video, args.time_duration, args.output)

    elif args.function == 'create_still_frame_narration_clip':
        if args.image is None:
            raise ValueError('Missing image input file path')
        if args.audio is None:
            raise ValueError('Missing audio input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        save_frame_at_time_as_image(args.image, args.audio, args.output)

    elif args.function == 'combine_videos':
        if args.text is None:
            raise ValueError('Missing text input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        combine_videos(args.text, args.output)
