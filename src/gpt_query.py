import base64
from typing import Optional
from dotenv import load_dotenv
from loguru import logger
from openai import ChatCompletion, OpenAI
import requests

from src.config import DEFAULT_MODEL, DEFAULT_POSITION, OUTPUT_FILE_NAME

SYS_PREFIX: str = "You are interviewing for a "
SYS_SUFFIX: str = """ position.
You will receive an audio transcription of the question. It may not be complete. You need to understand the question and write an answer to it. Otherwise, convey that you didn't understand and tell user to try again. \n
"""

SHORT_INSTRUCTION: str = "Concisely respond, limiting your answer to around 100 words. Provide Space/Time complexity for algorithms."
LONG_INSTRUCTION: str = "Limit long responses for code snippets. If asked about an algorithm, just provide the code, avoid extra text, avoid long one-liners. Default to Python if language is not mentioned. Provide example usage."

load_dotenv()

client: OpenAI = OpenAI()


def transcribe_audio(path_to_file: str = OUTPUT_FILE_NAME) -> str:
    """
    Transcribe audio from a file using the OpenAI Whisper API.

    Args:
        path_to_file (str, optional): Path to the audio file. Defaults to OUTPUT_FILE_NAME.

    Returns:
        str: The audio transcription.
    """
    logger.debug(f"Transcribing audio from: {path_to_file}...")

    with open(path_to_file, "rb") as audio_file:
        try:
            transcript: str = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file, response_format="text"
            )
        except Exception as error:
            logger.error(f"Can't transcribe audio: {error}")
            raise error

    logger.debug("Audio transcribed.")
    print("Transcription:", transcript)

    return transcript


def generate_answer(
    transcript: str,
    short_answer: bool = True,
    temperature: float = 0.7,
    model: str = DEFAULT_MODEL,
    position: str = DEFAULT_POSITION,
) -> str:
    """
    Generate an answer to the question using the OpenAI API.

    Args:
        transcript (str): The audio transcription.
        short_answer (bool, optional): Whether to generate a short answer. Defaults to True.
        temperature (float, optional): The temperature to use. Defaults to 0.7.
        model (str, optional): The model to use. Defaults to DEFAULT_MODEL.
        position (str, optional): The position to use. Defaults to DEFAULT_POSITION.

    Returns:
        str: The generated answer.
    """
    # Generate system prompt
    system_prompt: str = SYS_PREFIX + position + SYS_SUFFIX
    if short_answer:
        system_prompt += SHORT_INSTRUCTION
    else:
        system_prompt += LONG_INSTRUCTION

    # Generate answer
    try:
        response: ChatCompletion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
        )
    except Exception as error:
        logger.error(f"Can't generate answer: {error}")
        raise error

    return response.choices[0].message.content

def generate_image_answer(
    image_path: str,
    short_answer: bool = True,
    temperature: float = 0.2,
    model: str = DEFAULT_MODEL,
    position: str = DEFAULT_POSITION,
) -> str:
    """
    Analyze an image containing interview content and generate response.
    
    Short Answer: Identifies key question/problem in the image
    Long Answer: Detailed solution with analysis and improvements
    
    Args:
        image_path (str): Path to image file
        short_answer (bool): Concise problem ID vs detailed solution
        temperature (float): 0-2 creativity level
        model (str): GPT-4 vision model recommended
        position (str): Target job position context
    
    Returns:
        str: Analysis tailored to requested detail level
    """
    try:
        # Base system prompt
        sys_prompt = (f"You are analyzing technical interview content for a {position}. "
                     "The user will provide an image containing either:\n"
                     "- Algorithm challenges\n- Whiteboard designs\n- System diagrams\n- Code snippets\n\n")

        # Add instruction based on answer type
        if short_answer:
            sys_prompt += ("Concisely respond, limiting your answer to around 100 words. Provide Space/Time complexity for algorithms.")
        else:
            sys_prompt += ("Limit long responses for code snippets. If asked about an algorithm, just provide the code, avoid extra text, avoid long one-liners. Default to Python if language is not mentioned. Provide example usage.")

        # Encode image
        base64_image = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")

        # Construct messages
        messages = [
            {
                "role": "system", 
                "content": sys_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Analyze this technical interview content."
                    }
                ]
            }
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=600 if short_answer else 1500
        )

        return response.choices[0].message.content

    except Exception as error:
        logger.error(f"Image analysis failed: {error}")
        raise error
