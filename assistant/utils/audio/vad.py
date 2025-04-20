from typing import Callable
from pysilero_vad import SileroVoiceActivityDetector
import numpy as np
from collections import deque


class VadFilter:
    def __init__(
        self,
        callback: Callable,
        min_speech: int = 16,
        silence_end: int = 10,
        speech_threshold: float = 0.5,
        preroll_size: int = 16,
    ):
        self.vad = SileroVoiceActivityDetector()

        self.callback = callback

        self.min_speech = min_speech
        self.silence_end = silence_end
        self.speech_threshold = speech_threshold
        self.preroll_size = preroll_size

        self.speech_count = 0
        self.silence_count = 0
        self.speaking = False

        self.current_speech: np.ndarray = np.array([], dtype=np.int16)
        self.preroll_buffer = deque(maxlen=preroll_size)

    def __call__(self, chunk: np.ndarray) -> bool:
        self.preroll_buffer.append(chunk)
        speech_score = self.vad(chunk.tobytes())
        is_speech = speech_score >= self.speech_threshold

        if is_speech:
            self.speech_count += 1
            self.silence_count = 0

            if self.speech_count == self.min_speech:
                self.speaking = True
                self.current_speech = np.array([], dtype=np.int16)

                for preroll_chunk in self.preroll_buffer:
                    self.current_speech = np.concatenate([self.current_speech, preroll_chunk])

            elif self.speaking:
                self.current_speech = np.concatenate([self.current_speech, chunk])
        else:
            self.silence_count += 1

            if self.speaking:
                self.current_speech = np.concatenate([self.current_speech, chunk])

                if self.silence_count >= self.silence_end:
                    if self.callback and callable(self.callback):
                        self.callback(self.current_speech.copy())

                    self.speaking = False
                    self.speech_count = 0
                    self.silence_count = 0
                    self.current_speech = np.array([], dtype=np.int16)

        return is_speech
