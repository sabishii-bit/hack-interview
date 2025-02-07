import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger
from typing import Optional, List
from src.config import OUTPUT_FILE_NAME, SAMPLE_RATE

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames: List[np.ndarray] = []
        self.stream = None

    def find_blackhole_device(self) -> Optional[int]:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if "BlackHole" in dev["name"]:
                return idx
        return None

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        device_id = self.find_blackhole_device()
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            device=device_id,
            callback=self.audio_callback
        )
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status: {status}")
        if self.is_recording:
            self.frames.append(indata.copy())

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.save_recording()

    def save_recording(self):
        if self.frames:
            full_audio = np.concatenate(self.frames)
            sf.write(
                OUTPUT_FILE_NAME,
                full_audio,
                SAMPLE_RATE,
                format='WAV',
                subtype='PCM_16'
            )
            logger.info(f"Saved recording to {OUTPUT_FILE_NAME}")
