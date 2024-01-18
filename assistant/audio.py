import os
from datetime import datetime
from typing import Callable

import numpy as np
import resampy
import soundfile as sf
from pymumble_py3.constants import PYMUMBLE_SAMPLERATE
from pymumble_py3.soundqueue import SoundChunk


class AudioBufferHandler:
    def __init__(
        self,
        callback: Callable[[np.ndarray[np.float32]], None],
        target_samplerate: int,
        target_chunk_length_ms: int,
    ):
        """
        Initialize the AudioBufferHandler.

        :param callback: Callback where processed audio chunks will be forwarded.
        :param target_samplerate: The desired sample rate for the output audio.
        :param target_chunk_length_ms: The desired length of audio chunks in milliseconds.
        """
        self.callback = callback
        self.target_samplerate = target_samplerate
        self.target_chunk_length_ms = target_chunk_length_ms
        self.audio_buffer = np.array([], dtype=np.int16)
        self.input_samplerate = PYMUMBLE_SAMPLERATE

    def __call__(self, soundchunk: SoundChunk):
        """
        Callable method to handle incoming sound chunks.

        :param soundchunk: The incoming sound chunk.
        """
        # Process the incoming sound chunk
        self._process_chunk(soundchunk)

    def _process_chunk(self, soundchunk: SoundChunk):
        """
        Process the incoming sound chunk.

        :param soundchunk: The incoming sound chunk.
        """
        # Convert byte data to numpy array
        numpy_array = np.frombuffer(soundchunk.pcm, dtype=np.int16)

        # Append this chunk to the buffer
        self.audio_buffer = np.concatenate((self.audio_buffer, numpy_array))

        # Check if the buffer has reached the desired length
        if self._buffer_length_ms() >= self.target_chunk_length_ms:
            self._process_buffer()

    def _buffer_length_ms(self) -> float:
        """
        Calculate the length of the current buffer in milliseconds.

        :return: Length of the buffer in milliseconds.
        """
        return len(self.audio_buffer) / self.input_samplerate * 1000

    def _process_buffer(self):
        """
        Process the audio buffer.
        """
        # Calculate the number of samples corresponding to the target chunk length
        target_samples = int(self.target_chunk_length_ms / 1000 * self.input_samplerate)

        # Take only the necessary part of the buffer for processing
        buffer_to_process = self.audio_buffer[:target_samples]

        # Resample the buffer
        audio = buffer_to_process.astype(np.float32, order="C") / np.float32(
            np.iinfo(buffer_to_process.dtype).max
        )
        resampled = resampy.resample(
            audio, self.input_samplerate, self.target_samplerate
        )

        # Put the processed buffer in the output callback
        self.callback(resampled)

        # Retain the excess part of the buffer for the next chunk
        self.audio_buffer = self.audio_buffer[target_samples:]


def record_audio_chunk(
    chunk: np.ndarray[np.float32],
    directory: str,
    samplerate: int,
    audio_format: str = "FLAC",
) -> None:
    # Validate audio format
    if audio_format not in ["WAV", "FLAC"]:
        raise ValueError("Unsupported audio format. Please use 'WAV' or 'FLAC'.")

    # Use provided timestamp or generate a new one
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(directory, f"{timestamp}.{audio_format.lower()}")

    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)

    # Append the audio chunk to the file
    mode = "w" if not os.path.exists(filename) else "a"
    with sf.SoundFile(
        filename, mode=mode, samplerate=samplerate, channels=1, format=audio_format
    ) as file:
        file.write(chunk)
