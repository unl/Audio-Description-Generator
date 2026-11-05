""" Module for converting text to an audio file """
import argparse
import os
import uuid

import torch
from TTS.api import TTS

import ffmpeg_helper

def generate_audio(text:str, audio_output:str, model:str = 'tts_models/en/vctk/vits', language:str|None = None, speaker:str|None = 'p244', slow_down_percent:float=0.9):
    """ Takes in a string of text and saves an audio file of the narration of that text """

    # Get device && init TTS
    tts_device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tts_obj = TTS(model).to(tts_device)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_file_path = os.path.join(script_dir, 'tmp', f'{uuid.uuid4()}_tts.wav')

    tts_obj.tts_to_file(text=text, file_path=tmp_file_path, language=language, speaker=speaker)

    ffmpeg_helper.slow_down_audio_file(tmp_file_path, audio_output, slow_down_percent)

    _delete_tmp_file(tmp_file_path)

def _delete_tmp_file(file_path):
    """ Deletes file """

    if not os.path.exists(file_path):
        return

    if not os.path.isfile(file_path):
        raise ValueError('Trying to delete a non-file')

    file_path = os.path.abspath(file_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory_path = os.path.join(script_dir, '/tmp')
    if not os.path.dirname(file_path) == directory_path:
        raise ValueError('Trying to delete a file outside tmp folder')

    os.remove(file_path)

# -------------------------------
# CLI Entry
# -------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Detect audio blocks from audio input')
    parser.add_argument('-t',
                        '--text',
                        required=True,
                        help='Text to be converted to speech')
    parser.add_argument('-o',
                        '--output',
                        required=True,
                        help='Output file path')
    parser.add_argument('-m',
                        '--model',
                        default='tts_models/en/vctk/vits',
                        help='TTS model to run')
    parser.add_argument('-l',
                        '--language',
                        default='none',
                        help='TTS model language')
    parser.add_argument('-s',
                        '--speaker',
                        default='p244',
                        help='TTS model speaker')
    args = parser.parse_args()

    if args.language.lower() == 'none':
        args.language = None

    if args.speaker.lower() == 'none':
        args.speaker = None

    generate_audio(args.text, args.output, args.model, args.language, args.speaker)
