""" FFMPEG helper functions for running common commands """
import os
import math
import argparse
import subprocess

VIDEO_ENCODING = 'libx264'
ENCODER_PRESET = 'fast'
CONSTANT_RATE_FACTOR = '23'
PIXEL_FORMAT = 'yuv420p'
FRAME_RATE = '30'
FPS = int(FRAME_RATE)

AUDIO_ENCODING = 'aac'
BITRATE = '192k'
SAMPLE_RATE = '48000'
AUDIO_CHANNELS = '2'

# Intermediate clips (everything except the final export) store uncompressed audio.
# AAC adds encoder delay/padding to every file, and those few milliseconds add up
# when dozens of clips are concatenated. The final export re-encodes to AAC once.
INTERMEDIATE_AUDIO_ENCODING = 'pcm_s16le'

# Silence deliberately left after each narration before the video resumes
STILL_FRAME_AUDIO_PADDING_SECONDS = '0.5'
# Anything quieter than this at the end of the TTS output counts as "blank"
TTS_SILENCE_THRESHOLD = '-50dB'

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
    global DEBUG
    DEBUG = new_debug

def snap_to_frame(seconds: float) -> float:
    """ Rounds a time to the nearest frame boundary of the output frame rate """
    return round(seconds * FPS) / FPS

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
    """ Returns the duration (in seconds) of a media file """
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
    return int(result.stdout)


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
    """
    Based on the start time and end time it will cut the video and save a copy.
    Video and audio are both forced to be exactly (end - start) long, so the clip's
    audio can never run ahead of or behind its video once clips are joined.
    """
    duration = timecode_to_seconds(end_time) - timecode_to_seconds(start_time)

    # Re-encode the clip to avoid issues when it comes to key frames
    cmd = [
        'ffmpeg', '-y',
        # Video input
        '-i', video_input,
        # Seek to start time and keep exactly `duration` seconds
        '-ss', start_time, '-t', f'{duration:.6f}',
        '-avoid_negative_ts', 'make_zero', '-fflags', '+genpts',
        # Start both streams at 0 and pad audio with silence if the source audio is short
        '-vf', 'setpts=PTS-STARTPTS', '-af', 'asetpts=PTS-STARTPTS,apad',
        # Video settings
        '-c:v', VIDEO_ENCODING, '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        # Audio settings
        '-c:a', INTERMEDIATE_AUDIO_ENCODING, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
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

def prepare_narration_audio(audio_input:str, audio_output:str,
                            padding_seconds:float = float(STILL_FRAME_AUDIO_PADDING_SECONDS)):
    """
    Cleans up raw TTS output: trims the blank audio the TTS engine leaves at the end,
    converts to the project's sample rate/channels, and then adds exactly `padding_seconds`
    of silence. The result is a PCM wav, so its duration is exact and can be trusted.
    """
    # silenceremove only trims the *start* of a stream, so reverse -> trim -> reverse
    trim_end = (
        f'areverse,silenceremove=start_periods=1:start_threshold={TTS_SILENCE_THRESHOLD}'
        ':detection=peak,areverse'
    )
    filters = f'{trim_end},apad=pad_dur={padding_seconds}'

    cmd = [
        'ffmpeg', '-y', '-i', audio_input,
        '-af', filters,
        '-c:a', 'pcm_s16le', '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        audio_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def create_still_frame_narration_clip(audio_input:str, image_input:str, video_output:str):
    """
    Using the image and audio file it will create a still frame video.
    The clip length is the narration length rounded UP to a whole number of frames, and
    both the video and the audio are forced to exactly that length (audio is padded with
    silence). `audio_input` should come from prepare_narration_audio.
    """
    frames = max(1, math.ceil(get_duration(audio_input) * FPS - 1e-6))
    clip_duration = frames / FPS

    cmd = [
        'ffmpeg', '-y',
        # Loop image for the whole video
        '-loop', '1', '-framerate', FRAME_RATE, '-i', image_input,
        # Add narration track
        '-i', audio_input,
        # Pad the audio with silence (up to the frame boundary), then cut both streams
        # at exactly the same length. Replaces `-shortest`, which let the streams
        # end at slightly different times.
        '-af', 'apad', '-t', f'{clip_duration:.6f}',
        # Video settings
        '-c:v', VIDEO_ENCODING, '-tune', 'stillimage', '-preset', ENCODER_PRESET,
        '-crf', CONSTANT_RATE_FACTOR, '-pix_fmt', PIXEL_FORMAT, '-r', FRAME_RATE,
        # Audio settings
        '-c:a', INTERMEDIATE_AUDIO_ENCODING, '-ar', SAMPLE_RATE, '-ac', AUDIO_CHANNELS,
        video_output
    ]

    if not DEBUG:
        cmd.extend(['-loglevel', 'error'])

    subprocess.run(cmd, check=True)

def export_clips_to_file(clips_file_output:str, clips: list):
    """ Taking a list of clips (file paths) it will write it to a file for ffmpeg """
    with open(clips_file_output, 'w', encoding='utf-8') as clips_file:
        for clip in clips:
            # Paths in a concat list are relative to the list file (which lives in TMP_FOLDER)
            relative_clip = clip.replace(f'{TMP_FOLDER}/', '')
            clips_file.write(f'file {relative_clip}\n')

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
    parser = argparse.ArgumentParser(description='Run an ffmpeg helper function')
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
        else:
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
        save_frame_at_time_as_image(args.video, float(args.time_duration), args.output)

    elif args.function == 'prepare_narration_audio':
        if args.audio is None:
            raise ValueError('Missing audio input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        prepare_narration_audio(args.audio, args.output)

    elif args.function == 'create_still_frame_narration_clip':
        if args.image is None:
            raise ValueError('Missing image input file path')
        if args.audio is None:
            raise ValueError('Missing audio input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        create_still_frame_narration_clip(args.audio, args.image, args.output)

    elif args.function == 'combine_videos':
        if args.text is None:
            raise ValueError('Missing text input file path')
        if args.output is None:
            raise ValueError('Missing output file path')
        combine_videos(args.output, args.text)