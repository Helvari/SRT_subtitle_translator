# SRT Subtitle Translator

## Overview
SRT Subtitle Translator is a Python-based tool designed to automate the process of translating subtitles from one language to another. Utilizing OpenAI API, it ensures that the translated subtitles maintain the context and meaning of the original content.

## Features
- Reads SRT (SubRip Text) file format.
- Translates subtitles into the specified target language.
- Utilizes OpenAI and DeepL translation services.
- Saves translations to a SQLite database.
- Generates a new SRT file with the translated subtitles.
- Can overwrite existing translations or skip already translated entries.
- User input for setting translation parameters.

## Requirements
- Python 3.6 or higher
- openai Python library (for OpenAI translation)
- deepl Python library (for DeepL translation)
- colorama Python library (for terminal output coloring)
- dotenv Python library (for environment variable management)
- An .env file containing your API keys and other configuration settings.

## Setup and Configuration
1. Clone the repository to your local machine.
2. Install the required dependencies with pip install -r requirements.txt.
3. Set up an .env file in the root directory with the following contents:

  - OPENAI_API_KEY='your_openai_api_key'
  - DEEPL_API_KEY='your_deepl_api_key'
  - FILE_PATH='path_to_your_srt_file'

4. Ensure that the .env file is in the same directory as your main script.

## Usage

python main.py

Follow the on-screen prompts to select the translation service and specify translation parameters.

Type quit at any prompt to exit the application.


# Personal Project Notice
This program represents my first personal project and has been developed primarily for learning purposes. It is a reflection of my journey in software development, embodying the challenges and achievements I have encountered along the way.

As such, please note that the program is not perfect and may contain bugs or incomplete features. My main goal was to learn and grow from the experience of building it from scratch. I have decided to share it publicly not as a polished piece of software, but as a personal milestone and a stepping stone towards further learning and improvement.
