""" Module will take in a video and save a new audio description video """

import argparse
import os
import atexit
import uuid
import time

import ffmpeg_helper
import text_to_speech_ollama

DEBUG = False
SAVE_FILES = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_FOLDER = os.path.join(SCRIPT_DIR, 'tmp')


FILES = []

def _exit_handler():
    """ Cleans up files before exiting """

    for file_path in FILES:
        delete_tmp_file(file_path)

atexit.register(_exit_handler)

def delete_tmp_file(file_path):
    """ Deletes file """
    if SAVE_FILES:
        return

    if not os.path.exists(file_path):
        return

    if not os.path.isfile(file_path):
        raise ValueError('Trying to delete a non-file')

    file_path = os.path.abspath(file_path)
    if not os.path.dirname(file_path) == TMP_FOLDER:
        raise ValueError('Trying to delete a file outside tmp folder')

    os.remove(file_path)

def format_elapsed_time(elapsed_seconds: float) -> str:
    """ Returns a formatted time string for printing"""
    minutes = int(elapsed_seconds // 60)
    seconds = int(elapsed_seconds % 60)
    return f"{minutes}m {seconds}s"

def debug_print(message, extra_new_line:bool = False):
    """ Print message is DEBUG is true """
    if DEBUG:
        if extra_new_line:
            print(message, end=os.linesep+os.linesep)
        else:
            print(message)

def process_video(script_input:str, video_input:str, video_output:str):
    """ Takes in video and saves an audio description version of the video """

    video_uuid = uuid.uuid4()

    debug_print('Processing Video')
    debug_print(f'Video UUID: {video_uuid}')

    # Make tmp dir if not exists
    os.makedirs(TMP_FOLDER, exist_ok=True)
    tmp_path = f'{TMP_FOLDER}/{video_uuid}_'

    clips = []
    previous_time = 0
    next_time = 0
    total_duration = ffmpeg_helper.get_duration(video_input)

    debug_print(f'Total Duration: {total_duration}', True)

    line_count = 0
    with open(script_input, 'r', encoding="utf-8") as file:
        for current_line in file:
            current_line = current_line.strip()
            if not current_line:
                continue  # skip empty lines

            line_count += 1

            debug_print(f'Line {line_count}')

            # Split on the first space only
            time_str, text = current_line.split(" ", 1)

            # Convert the first part to float
            timestamp = float(time_str)

            debug_print(f'Time: {timestamp}')
            debug_print(f'Text: {text}')

            debug_print('Generating TTS')
            # Generate TTS
            narration_track_path = f'{tmp_path}{line_count}_narration_track.wav'
            FILES.append(narration_track_path)
            text_to_speech_ollama.generate_audio(text, narration_track_path)

            next_time = timestamp

            if next_time != previous_time:
                clip_start = ffmpeg_helper.seconds_to_timecode(previous_time)
                clip_end = ffmpeg_helper.seconds_to_timecode(next_time)
                debug_print(f'Clipping at {clip_start} to {clip_end}')

                clip_path = f'{tmp_path}{line_count}_video_clip.mp4'
                FILES.append(clip_path)
                ffmpeg_helper.cut_video_into_clip(video_input, clip_path, clip_start, clip_end)
                clips.append(clip_path)

            debug_print('Getting video frame')
            frame_at_time_path = f'{tmp_path}{line_count}_video_frame.png'
            FILES.append(frame_at_time_path)
            ffmpeg_helper.save_frame_at_time_as_image(video_input, timestamp, frame_at_time_path, 0)

            debug_print('Generating narration clip')
            narration_clip_path = f'{tmp_path}{line_count}_narration_clip.mp4'
            FILES.append(narration_clip_path)
            ffmpeg_helper.create_still_frame_narration_clip(narration_track_path, frame_at_time_path, narration_clip_path)
            clips.append(narration_clip_path)

            previous_time = next_time

            debug_print('Deleting narration track and video frame')
            delete_tmp_file(narration_track_path)
            delete_tmp_file(frame_at_time_path)

    if previous_time != total_duration:
        clip_start = ffmpeg_helper.seconds_to_timecode(previous_time)
        clip_end = ffmpeg_helper.seconds_to_timecode(total_duration)
        debug_print(f'Clipping at {clip_start} to {clip_end}', True)

        clip_path = f'{tmp_path}final_video_clip.mp4'
        FILES.append(clip_path)
        ffmpeg_helper.cut_video_into_clip(video_input, clip_path, clip_start, clip_end)
        clips.append(clip_path)

    debug_print('Exporting Clips', True)
    clips_file_path = f'{tmp_path}clips_file.txt'
    FILES.append(clips_file_path)
    ffmpeg_helper.export_clips_to_file(clips_file_path, clips)

    debug_print('Combining Clips')
    ffmpeg_helper.combine_videos(video_output, clips_file_path)

    debug_print('Finished and cleaning up files')
    _exit_handler()

# -------------------------------
# CLI Entry
# -------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate audio-described video based on narration script.')
    parser.add_argument('-it',
                        '--input_text',
                        required=True,
                        help='Path to narration script file')
    parser.add_argument('-iv',
                        '--input_video',
                        required=True,
                        help='Path to video file')
    parser.add_argument('-ov',
                        '--output_video',
                        required=True,
                        help='Path to final video output file')
    parser.add_argument('-ve',
                        '--video_encoding',
                        default=ffmpeg_helper.VIDEO_ENCODING,
                        help='Video encoding for ffmpeg')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug mode')
    parser.add_argument('--ffmpeg_debug',
                        action='store_true',
                        help='FFMPEG debug mode')
    parser.add_argument('--save_files',
                        action='store_true',
                        help='Save tmp files')
    args = parser.parse_args()

    if args.debug is True:
        DEBUG = True

    if args.ffmpeg_debug is True:
        ffmpeg_helper.set_debug(True)

    if args.save_files is True:
        SAVE_FILES = True

    ffmpeg_helper.set_video_encoding(args.video_encoding)

    # Record the start time
    start_time = time.time()

    try:
        process_video(args.input_text, args.input_video, args.output_video)

        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        debug_print(format_elapsed_time(elapsed_time))

    except KeyboardInterrupt:
        _exit_handler()
