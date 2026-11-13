""" Module for detecting audio blocks """
import argparse
import os
import whisper
import ffmpeg_helper

DEBUG = False

def debug_print(message, extra_new_line:bool = False):
    """ Print message is DEBUG is true """
    if DEBUG:
        if extra_new_line:
            print(message, end=os.linesep+os.linesep)
        else:
            print(message)

def get_audio_blocks(audio_input:str, min_pause:float=0.6, min_confidence:float=0.4):
    """
    Returns both speech and pause blocks based on word-level timestamps.
    Uses Whisper's own segmentation (not amplitude-based silence).
    """

    total_duration = ffmpeg_helper.get_duration(audio_input)

    model = whisper.load_model("base")
    result = model.transcribe(
        audio_input,
        fp16=False,
        word_timestamps=True,
        condition_on_previous_text=False
    )

    # Flatten all words from all segments
    words = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                # Some Whisper variants use `probability`, others `avg_logprob`
                conf = w.get("probability", None)
                if conf is None:
                    # Convert avg_logprob (typically around -0.2 to -1.2) to a rough probability
                    conf = pow(10, w.get("avg_logprob", -1))
                w["confidence"] = conf
                words.append(w)

    # Filter out low-confidence words
    words = [w for w in words if w["confidence"] >= min_confidence]

    if not words:
        return []

    blocks = []
    block_count = 0

    text_buffer = ''
    text_buffer_start = 0.0
    text_buffer_end = 0.0

    # Iterate through all recognized words
    for single_word in words:
        current_word_start = float(single_word["start"])
        current_word_end = float(single_word["end"])
        gap = current_word_start - text_buffer_end

        debug_print(single_word, gap)

        # We found a big enough gap in the speech so we should save the buffer
        if gap > min_pause:
            if text_buffer_start != text_buffer_end:
                blocks.append({
                    "scene_number": block_count,
                    "text": text_buffer.strip(),
                    "start_timecode": ffmpeg_helper.seconds_to_timecode(text_buffer_start),
                    "end_timecode": ffmpeg_helper.seconds_to_timecode(text_buffer_end)
                })
            text_buffer = ''
            text_buffer_start = current_word_start - gap
            block_count += 1

        text_buffer_end = current_word_end
        text_buffer += single_word['word']

    # Get the last block
    blocks.append({
        "scene_number": block_count,
        "text": text_buffer.strip(),
        "start_timecode": ffmpeg_helper.seconds_to_timecode(text_buffer_start),
        "end_timecode": ffmpeg_helper.seconds_to_timecode(text_buffer_end)
    })

    # Add a block for the end of the video
    if text_buffer_end < total_duration:
        blocks.append({
            "scene_number": block_count + 1,
            "text": '',
            "start_timecode": ffmpeg_helper.seconds_to_timecode(text_buffer_end),
            "end_timecode": ffmpeg_helper.seconds_to_timecode(total_duration)
        })

    return blocks

# -------------------------------
# CLI Entry
# -------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Detect audio blocks from audio input')
    parser.add_argument('-i',
                        '--input',
                        required=True,
                        help='Path to input audio file')
    parser.add_argument('-ml',
                        '--min_length',
                        default='0.6',
                        help='Minimum length for audio block')
    parser.add_argument('-mc',
                        '--min_confidence',
                        default='0.4',
                        help='Minimum confidence for keeping a word')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug mode')
    args = parser.parse_args()

    print(get_audio_blocks(args.input, float(args.min_length)))
