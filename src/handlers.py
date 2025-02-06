from typing import Any, Dict

import PySimpleGUI as sg
from loguru import logger

from src import audio, gpt_query
from src.button import OFF_IMAGE, ON_IMAGE


def handle_events(window: sg.Window, event: str, values: Dict[str, Any]) -> None:
    """
    Handle the events. Record audio, transcribe audio, generate quick and full answers.
    """
    try:
        # Safely get focused element with error handling
        focused_element: sg.Element = None
        try:
            focused_element = window.find_element_with_focus()
        except KeyError as e:
            if 'popdown' in str(e):
                # Ignore internal Tkinter popdown focus issues
                return
            raise

        # Process events only if not focused on position input or no focus
        position_input_focused = (
            focused_element and 
            hasattr(focused_element, 'Key') and 
            focused_element.Key == "-POSITION_INPUT-"
        )
        
        if not position_input_focused:
            if event in ("r", "R", "-RECORD_BUTTON-"):
                recording_event(window)
            elif event in ("a", "A", "-ANALYZE_BUTTON-"):
                transcribe_event(window)

    except Exception as e:
        logger.error(f"Error handling events: {str(e)}")
        return

    # Rest of the event handling remains the same
    if event[:6] in ("Return", "Escape"):
        window["-ANALYZE_BUTTON-"].set_focus()

    elif event == "-WHISPER-":
        answer_events(window, values)

    elif event == "-QUICK_ANSWER-":
        logger.debug("Quick answer generated.")
        window["-QUICK_ANSWER-"].update(values["-QUICK_ANSWER-"])

    elif event == "-FULL_ANSWER-":
        logger.debug("Full answer generated.")
        window["-FULL_ANSWER-"].update(values["-FULL_ANSWER-"])


def recording_event(window: sg.Window) -> None:
    """
    Handle the recording event. Record audio and update the record button.

    Args:
        window (sg.Window): The window element.
    """
    button: sg.Element = window["-RECORD_BUTTON-"]
    button.metadata.state = not button.metadata.state
    button.update(image_data=ON_IMAGE if button.metadata.state else OFF_IMAGE)

    # Record audio
    if button.metadata.state:
        window.perform_long_operation(lambda: audio.record(button), "-RECORDED-")


def transcribe_event(window: sg.Window) -> None:
    """
    Handle the transcribe event. Transcribe audio and update the text area.

    Args:
        window (sg.Window): The window element.
    """
    transcribed_text: sg.Element = window["-TRANSCRIBED_TEXT-"]
    transcribed_text.update("Transcribing audio...")

    # Transcribe audio
    window.perform_long_operation(gpt_query.transcribe_audio, "-WHISPER-")


def answer_events(window: sg.Window, values: Dict[str, Any]) -> None:
    """
    Handle the answer events. Generate quick and full answers and update the text areas.

    Args:
        window (sg.Window): The window element.
        values (Dict[str, Any]): The values of the window.
    """
    transcribed_text: sg.Element = window["-TRANSCRIBED_TEXT-"]
    quick_answer: sg.Element = window["-QUICK_ANSWER-"]
    full_answer: sg.Element = window["-FULL_ANSWER-"]

    # Get audio transcript and update text area
    audio_transcript: str = values["-WHISPER-"]
    transcribed_text.update(audio_transcript)

    # Get model and position
    model: str = values["-MODEL_COMBO-"]
    position: str = values["-POSITION_INPUT-"]

    # Generate quick answer
    logger.debug("Generating quick answer...")
    quick_answer.update("Generating quick answer...")
    window.perform_long_operation(
        lambda: gpt_query.generate_answer(
            audio_transcript,
            short_answer=True,
            temperature=0,
            model=model,
            position=position,
        ),
        "-QUICK_ANSWER-",
    )

    # Generate full answer
    logger.debug("Generating full answer...")
    full_answer.update("Generating full answer...")
    window.perform_long_operation(
        lambda: gpt_query.generate_answer(
            audio_transcript,
            short_answer=False,
            temperature=0.7,
            model=model,
            position=position,
        ),
        "-FULL_ANSWER-",
    )
