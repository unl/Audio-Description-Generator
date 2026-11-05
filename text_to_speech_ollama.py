""" Module for converting text to an audio file """
import argparse

import subprocess

def generate_audio(text:str, audio_output:str, model:str = 'phonon', voice:str|None = 'Miles', ollama_command:str|None = 'ollama'):
    """ Takes in a string of text and saves an audio file of the narration of that text """

    with open(audio_output, "wb") as f:
        subprocess.run([ollama_command, 'run', model, '--voice', voice, text], stdout=f, check=True)

# -------------------------------
# CLI Entry
# -------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts text to speech')
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
                        default='phonon',
                        help='TTS model to run')
    parser.add_argument('-v',
                        '--voice',
                        default='Miles',
                        help='TTS model voice')
    parser.add_argument('-oc',
                        '--ollama_command',
                        default='Ollama',
                        help='Path to Ollama executable')
    args = parser.parse_args()

    generate_audio(args.text, args.output, args.model, args.voice, args.ollama_command)
