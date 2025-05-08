from typing import List, Tuple, Union
import resampy
import numpy as np
from voice_forge import PiperTts
from pymumble_py3.constants import PYMUMBLE_SAMPLERATE
from assistant.utils import create_empty_audio
from assistant.config import (
    PIPER_MODELS_LOCATION
)


class Synthesizer:
    def __init__(self, mumble, piper_models_location: str = PIPER_MODELS_LOCATION):
        self.mumble = mumble
        self.piper_models_location = piper_models_location
        self.commands: List[Tuple[str, Union[str, float]]] = []
        self.current_tts_name: str = None
        self.tts_cache = {}

    def tts(self, tts_name: str):
        self.current_tts_name = tts_name
        if tts_name not in self.tts_cache:
            self.tts_cache[tts_name] = PiperTts(tts_name, self.piper_models_location)
        return self

    def say(self, text: str):
        if not self.current_tts_name:
            raise ValueError("No TTS selected before calling say(). Use .tts(tts_name) first.")
        self.commands.append(("say", (self.current_tts_name, text)))
        return self

    def silence(self, seconds: float):
        self.commands.append(("silence", seconds))
        return self

    def run(self, start_ms: int = 100, span_ms: int = 100, end_ms: int = 100):
        audio_sequence = []

        start = create_empty_audio(start_ms, PYMUMBLE_SAMPLERATE, np.int16)
        span = create_empty_audio(span_ms, PYMUMBLE_SAMPLERATE, np.int16)
        end = create_empty_audio(end_ms, PYMUMBLE_SAMPLERATE, np.int16)

        audio_sequence.append(start)

        for idx, (cmd_type, value) in enumerate(self.commands):
            if cmd_type == "say":
                tts_name, text = value
                tts_engine = self.tts_cache[tts_name]
                audio_data, sample_rate = tts_engine.synthesize_stream(text)
                resampled = resampy.resample(audio_data, sample_rate, PYMUMBLE_SAMPLERATE)
                audio_sequence.append(resampled)
            elif cmd_type == "silence":
                silence_sec = value
                silence_ms = int(silence_sec * 1000)
                silence_audio = create_empty_audio(silence_ms, PYMUMBLE_SAMPLERATE, np.int16)
                audio_sequence.append(silence_audio)

            # Add span between commands unless it's the last one
            if idx < len(self.commands) - 1:
                audio_sequence.append(span)

        audio_sequence.append(end)

        final_audio = np.concatenate(audio_sequence).astype(np.int16).tobytes()
        self.mumble.sound_output.add_sound(final_audio)

        # Clear the sequence after run
        self.commands.clear()

