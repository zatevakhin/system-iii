# %% Interactive tests for Voice subsystem

# %% Install required dependencies for tests
!pip install git+https://github.com/zatevakhin/voice-forge.git piper-tts

# %% Import required modules
import pymumble_py3
import numpy as np
import resampy
import time
from voice_forge import PiperTts
from pymumble_py3.constants import PYMUMBLE_SAMPLERATE
from assistant.utils import enrich_with_silence, create_empty_audio
from assistant.config import (
    PIPER_MODELS_LOCATION
)

# %% Create TTS voices used for testing
tts_en_01 = PiperTts("en_US-amy-low", PIPER_MODELS_LOCATION)
tts_en_02 = PiperTts("en_GB-aru-medium", PIPER_MODELS_LOCATION)
tts_ua = PiperTts("uk_UA-lada-x_low", PIPER_MODELS_LOCATION)
tts_ru = PiperTts("ru_RU-irina-medium", PIPER_MODELS_LOCATION)

# %% Connect client to a Mumble server
mumble = pymumble_py3.Mumble(host="127.0.0.1", user="test")
mumble.set_receive_sound(True)
mumble.start()
mumble.is_ready() # waits connection

# %% Define helper function that performs TTS and streaming into Mumble
def synthesize_and_send(mumble: pymumble_py3.Mumble, tts_list: list[PiperTts],
                                 text_list: list[str], start_ms: int = 100, span_ms: int = 100, end_ms: int = 100):
    assert len(tts_list) == len(text_list), "Number of TTS voices must match number of text chunks"

    resampled_chunks = []

    for i in range(len(tts_list)):
        audio_data, sample_rate = tts_list[i].synthesize_stream(text_list[i])
        resampled = resampy.resample(audio_data, sample_rate, PYMUMBLE_SAMPLERATE)
        resampled_chunks.append(resampled)

    start = create_empty_audio(start_ms, PYMUMBLE_SAMPLERATE, np.int16)
    span = create_empty_audio(span_ms, PYMUMBLE_SAMPLERATE, np.int16)
    end = create_empty_audio(end_ms, PYMUMBLE_SAMPLERATE, np.int16)

    audio_sequence = [start]

    for i, chunk in enumerate(resampled_chunks):
        audio_sequence.append(chunk)
        if i < len(resampled_chunks) - 1:
            audio_sequence.append(span)

    audio_sequence.append(end)

    sound = np.concatenate(audio_sequence).astype(np.int16).tobytes()
    mumble.sound_output.add_sound(sound)


# %% Test 1
synthesize_and_send(mumble, [tts_en_01], ["Why is the sky blue?"])
# %% Test 1
synthesize_and_send(mumble, [tts_en_02], ["Why is the sky blue?"])
# %% Test 2
synthesize_and_send(mumble, [tts_ua], ["Чому небо блакитне?"])
# %% Test 3
synthesize_and_send(mumble, [tts_ru], ["Почему небо голубое?"])

# %% Test 4
synthesize_and_send(mumble, [tts_en_01, tts_en_02], ["Why is the sky blue?", "Why is the sky red?"], 50)

# %% Test 5
synthesize_and_send(mumble, [tts_en_01, tts_en_02], ["Why is the sky blue?", "The sky appears blue due to a phenomenon called Rayleigh scattering."], 200)
