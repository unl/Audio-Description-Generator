""" Detecting the semantic scenes using Open Ai's Clip """

import os
import argparse
import atexit

import torch
import clip
from PIL import Image

import ffmpeg_helper

SAVE_FILES = False
FILES = []
DEBUG = False

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory_path = os.path.join(script_dir, 'tmp')
    if not os.path.dirname(file_path) == directory_path:
        raise ValueError('Trying to delete a file outside tmp folder')

    os.remove(file_path)

def debug_print(message, extra_new_line:bool = False):
    """ Print message is DEBUG is true """
    if DEBUG:
        if extra_new_line:
            print(message, end=os.linesep+os.linesep)
        else:
            print(message)

def _get_embedding(frame_path, model, preprocess, device):
    """ Convert an image file to a normalized CLIP embedding """
    image = Image.open(frame_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding

def _compute_cosine_similarity(a, b):
    """ Determines how similar two tensors are """
    # pylint: disable=not-callable
    return torch.nn.functional.cosine_similarity(a, b).item()

def get_visual_scenes(video_path:str, seconds_per_check:int=2, threshold:float=0.85) -> list:
    """ Detect semantic scene changes in a video using CLIP embeddings """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)

    duration = ffmpeg_helper.get_duration(video_path)

    prev_emb = None
    scenes = []
    current_scene_start = 0.0
    scene_number = 1

    for frame_index in range(0, int(duration), seconds_per_check):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tmpdir = os.path.join(script_dir, 'tmp', f'frame_{frame_index}.png')
        FILES.append(tmpdir)

        debug_print(f'Frame: {frame_index} of {int(duration)}')

        ffmpeg_helper.save_frame_at_time_as_image(video_path, frame_index, tmpdir, 224)
        emb = _get_embedding(tmpdir, model, preprocess, device)

        if prev_emb is not None:
            sim = _compute_cosine_similarity(emb, prev_emb)
            if sim < threshold:
                # Scene boundary detected
                scenes.append({
                    "scene_number": scene_number,
                    "start_timecode": ffmpeg_helper.seconds_to_timecode(current_scene_start),
                    "end_timecode": ffmpeg_helper.seconds_to_timecode(frame_index)
                })
                scene_number += 1
                current_scene_start = frame_index

        prev_emb = emb
        delete_tmp_file(tmpdir)

    # Add the last scene
    scenes.append({
        "scene_number": scene_number,
        "start_timecode": ffmpeg_helper.seconds_to_timecode(current_scene_start),
        "end_timecode": ffmpeg_helper.seconds_to_timecode(duration)
    })

    _exit_handler()

    return scenes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Semantic scene detection using CLIP and ffmpeg."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Path to the input video file"
    )
    parser.add_argument(
        "-sc",
        "--seconds_per_check",
        type=int,
        default=2,
        help="Seconds between analyzed frames (default: 2.0)"
    )
    parser.add_argument(
        "-st",
        "--scene_threshold",
        type=float,
        default=0.85,
        help="Cosine similarity threshold for scene change (default: 0.85)"
    )
    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug mode')

    args = parser.parse_args()

    if args.debug is True:
        DEBUG = True

    try:
        debug_print('Processing')
        resulting_scenes = get_visual_scenes(args.input, args.seconds_per_check, args.scene_threshold)

        debug_print('\nDetected scenes:')
        for single_scene in resulting_scenes:
            print(f"Scene: {single_scene['scene_number']:03d}, Start:{single_scene['start_timecode']}, End:{single_scene['end_timecode']}")

    except KeyboardInterrupt:
        _exit_handler()
