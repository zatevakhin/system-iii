import logging

from assistant.components.llm import QueryResponse
from assistant.components.synthesis import Sentence
from .util import ensure_model_exists
from .event_bus import EventBus, EventType
from langchain_ollama import OllamaLLM

from assistant.config import (
    OLLAMA_LLM_TEMPERATURE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL_KEEP_ALIVE
)

logger = logging.getLogger(__name__)


class InterruptOr:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.event_bus.subscribe(EventType.TRANSCRIPTION_DONE, self.on_query)
        self.event_bus.subscribe(EventType.LLM_INFERENCE_STATUS, self.on_inference_status)
        self.event_bus.subscribe(EventType.LLM_STREAM_DONE, self.on_llm_stream_done)
        self.event_bus.subscribe(EventType.MUMBLE_PLAYING_STATUS, self.on_mumble_playing_status)
        self.event_bus.subscribe(EventType.MUMBLE_NOW_PLAYING, self.on_mumble_now_playing)
        self.event_bus.subscribe(EventType.TRANSCRIPTION_STATUS, self.on_transcription_status)
        self.event_bus.subscribe(EventType.SPEECH_SYNTH_STATUS, self.on_speech_synthesis_status)

        self.llm = self.create_llm("phi3:3.8b")

        self.running = False
        logger.info(f"{__name__} ... IDLE")

    @staticmethod
    def create_llm(model: str):
        ensure_model_exists(OLLAMA_BASE_URL, model)

        logger.info(f"Creating Ollama using '{model}' model.")
        return OllamaLLM(
            base_url=OLLAMA_BASE_URL,
            model=model,
            temperature=OLLAMA_LLM_TEMPERATURE,
            keep_alive=OLLAMA_MODEL_KEEP_ALIVE,
        )

    def on_query(self, query: str):
        logger.info(f"on_query({query})")

    def on_inference_status(self, query: str):
        logger.info(f"on_inference_status('{query}')")

    def on_llm_stream_done(self, query: QueryResponse):
        logger.info(f"on_llm_stream_done({query}, {len(query.tokens)})")

    def on_mumble_playing_status(self, query: str):
        logger.info(f"on_mumble_playing_status('{query}')")

    def on_mumble_now_playing(self, sentence: Sentence):
        logger.info(f"on_mumble_now_playing({sentence})")

    def on_transcription_status(self, query: str):
        logger.info(f"on_transcription_status('{query}')")

    def on_speech_synthesis_status(self, query: str):
        logger.info(f"on_speech_synthesis_status('{query}')")

    def run(self):
        self.running = True
        logger.info(f"{__name__} ... OK")

    def stop(self):
        logger.info(f"{__name__} ... STOPPING")
        self.running = False
        logger.info(f"{__name__} ... DEAD")
