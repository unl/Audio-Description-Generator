# Audio Description Project

A CLI based audio description generation tool built on Python leveraging the power of Ollama, Whisper, CLIP, Coqui TTS and FFMPEG.

## Installation

Installation is written for MacOS

1. Install python 3.14
2. Install FFMPEG and Ollama and espeak
    - Run `brew install ffmpeg` for video editing
    - Run `brew install espeak` for some AI Text-To-Speech
    - Install Ollama from their site [https://ollama.com/download](https://ollama.com/download)
3. Run `ollama pull gemma3:12b` and `ollama pull nomic-embed-text`
4. Run `python3 -m venv ./venv` && `source ./venv/bin/activate`
    - Every time you start a new terminal for the project run `source ./venv/bin/activate`
    - [Python Environments](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-python-envs) will run that for you
5. Run `pip3 install -r requirements.txt`
6. Run `python3 ./describe_video.py --input ./my_video.mp4 --output ./my_video_script.txt` to generate a video script file
7. Then run `python3 ./process_video.py --input_video ./my_video.mp4 --input_text ./my_video_script.txt --output ./my_video_audio_description.mp4`

## Pylint

To run pylint, run`pylint ./describe_video.py`. Pylint configuration is located in `./pyproject.toml`
