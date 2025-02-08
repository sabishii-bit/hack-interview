# Hack Interview

## Overview

Hack Interview application is a tool designed to assist in job interviews using the power of Generative AI. Combining voice recognition and text generation technologies, this application transcribes interview questions and generates responses in real-time, empowering users to handle interviews with confidence and ease. This application is a fork of the [hack-interview](https://github.com/ivnvxd/hack-interview) tool made by [ivnvxd](https://github.com/ivnvxd), made with an updated user interface that displays Markdown and brings new functionality for more versatility in real-world settings.

## ⚠️ Disclaimer ⚠️

> This application is a proof of concept and should be used **ethically** and **responsibly**. It is not intended to deceive or mislead during interviews. The primary purpose is to demonstrate the capabilities of AI in assisting with real-time question understanding and response generation. Users should use this tool **only** for practice and learning!

## Features

# Old
- **Real-Time Audio Processing**: Records and transcribes audio seamlessly.
- **Voice Recognition**: Uses OpenAI's Whisper model for accurate voice recognition.
- **Intelligent Response Generation**: Leverages OpenAI's GPT models for generating concise and relevant answers.
- **Cross-Platform Functionality**: Designed to work on various operating systems.
- **User-Friendly Interface**: Simple, intuitive and hideous GUI for easy interaction.

# New
- **Real-Time Image Processing**: Allows users to discretely screenshot their working window for whiteboarding challenges done on the fly, ChatGPT interprets the context and provides answers.
- **Global Key Listeners**: Listens to user-input even when the window isn't in focus, allowing discrete control of the application while screen-sharing.
- **Key Binding Configuration**: Allows users to edit their key bindings.
- **Updated User Interface**: This forked project builds off of the previous work allowing Markdown to be rendered in the application.

# TODO:
- Create functionality for continuous hands-off context streaming from audio to ChatGPT, retrieving a continuous stream of responses.
- Record internal audio from the PC instead of only listening to user microphone.
- Improve on GUI. Looks rough.
- Implement a show/hide hotkey to hide the GUI at will.

## Requirements

- **Python 3.11.9**: Ensure correct Python version is installed on your system. Preferred method is pyenv.
- **OpenAI API Key**: To use OpenAI's GPT models, you will need an API key.
- **Windows 10+**: This fork leverages the Win32 API and needs it to run.

## Usage

- **Installing Dependencies**: `pip install -r requirements.txt`
- **Starting the Application**: Run `python main.py` to launch the GUI.
