from typing import List, Optional
import logging
from assistant.components.watchdog.main import WatchdogSourceInfo
import numpy as np
from datetime import datetime
from numpy._core.multiarray import ndarray
import torch
from pyannote.audio import Model
from queue import Queue
import threading
from pydantic import BaseModel, Field
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from typing import Protocol, Union


from assistant.config import SPEECH_PIPELINE_SAMPLERATE
from assistant.core.component import Component
from assistant.core import service
from assistant.components.mumble.mumble import SourceInfo, SpeechSegment
from assistant.utils.utils import observe
from .events import VOICE_ID_SPEAKER_ENROLLED, VOICE_ID_SPEAKER_IDENTIFIED


class IdentifiedSpeaker(BaseModel):
    speaker_id: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)


class VoiceID(Component):
    @property
    def version(self) -> str:
        return "0.0.1"

    @property
    def events(self) -> List[str]:
        return [
            VOICE_ID_SPEAKER_IDENTIFIED,
            VOICE_ID_SPEAKER_ENROLLED,
        ]

    def initialize(self) -> None:
        super().initialize()

        # Load configuration
        self.similarity_threshold = self.get_config("similarity_threshold", 0.75)
        self.min_speech_duration = self.get_config("min_speech_duration", 0.5)
        self.known_speakers_collection = self.get_config(
            "known_speakers_collection", "speaker_embeddings"
        )
        self.unknown_speakers_collection = self.get_config(
            "unknown_speakers_collection", "unknown_speaker_embeddings"
        )

        self.qdrant_host = self.get_config("qdrant_host", "localhost")
        self.qdrant_port = self.get_config("qdrant_port", 6334)

        self.speech_segments = Queue()
        self.speech_segments_observer = observe(
            self.speech_segments, self.process_speech, threaded=True
        )

        self.recognizer = SpeakerRecognizer(
            self.qdrant_host,
            self.qdrant_port,
            self.known_speakers_collection,
            self.unknown_speakers_collection,
        )

        # Initialize model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.logger.info(f"Component '{self.name}' initialized")

    def shutdown(self) -> None:
        super().shutdown()
        self.logger.info(f"Component '{self.name}' shutdown complete")

    def on_speech(self, segment: SpeechSegment) -> None:
        self.logger.info(f"Received segment: {segment.segment_id}")
        self.speech_segments.put_nowait(segment)

    def process_speech(self, segment: SpeechSegment) -> None:
        self.logger.info(f"Processing segment: {segment.segment_id}")
        if speaker := self.recognizer.identify_speaker(segment.data, 0.75):
            self.logger.info(f"Recognized speaker: {speaker}")
        else:
            self.recognizer.enroll_unknown(segment)

            if isinstance(segment.source_info, WatchdogSourceInfo):
                self.logger.info(
                    f"Speaker from '{segment.source}' segment '{segment.segment_id}' from '{segment.source_info.file}' was not recognized"
                )
            elif isinstance(segment.source_info, SourceInfo):
                self.logger.info(
                    f"Speaker from '{segment.source}' segment '{segment.segment_id}' from '{segment.source_info.user}' was not recognized"
                )
            else:
                self.logger.info(
                    f"Speaker from '{segment.source}' segment '{segment.segment_id}' was not recognized"
                )


class SpeakerRecognizer:
    def __init__(
        self,
        host,
        grpc_port,
        known_speakers,
        unknown_speakers,
        hf_token=None,
    ):
        self.logger = logging.getLogger("component.voice_id.recognizer")
        self.logger.setLevel(logging.INFO)
        self.client = QdrantClient(host=host, grpc_port=grpc_port, prefer_grpc=True)
        self.known_speakers = known_speakers
        self.unknown_speakers = unknown_speakers
        self.embedding_size = 512
        self._initialize_collection(self.known_speakers)
        self._initialize_collection(self.unknown_speakers)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Using '{device}' device for embedding computation.")
        self.model = Model.from_pretrained(
            "pyannote/embedding", use_auth_token=hf_token
        )
        self.model.eval()
        self.device = device
        self.model = self.model.to(device)

    def _initialize_collection(self, new_collection: str) -> None:
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]

            if new_collection not in collection_names:
                self.client.create_collection(
                    collection_name=new_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_size, distance=Distance.COSINE
                    ),
                )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Qdrant collection: {str(e)}")

    def _extract_embedding(self, data: np.ndarray) -> np.ndarray:
        if len(data.shape) > 1:
            data = data[:, 0]

        if data.dtype != np.int16:
            data = (data * 32768).astype(np.int16)

        waveform = torch.tensor(data, dtype=torch.float32) / 32768.0
        waveform = waveform.unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model(waveform)

        return embedding.cpu().numpy().flatten()

    def enroll_known(self, data: np.ndarray, speaker_id: str):
        self._enroll_speaker(self.known_speakers, data, {"speaker_id": speaker_id})

    def enroll_unknown(self, segment: SpeechSegment):
        self._enroll_speaker(
            self.unknown_speakers, segment.data, {"source": segment.source}
        )

    def _enroll_speaker(
        self, collection_name: str, data: np.ndarray, payload: Optional[dict] = None
    ) -> bool:
        try:
            embedding_np = self._extract_embedding(data)
            if np.isnan(embedding_np).any() or np.isinf(embedding_np).any():
                return False

            point_id = str(uuid.uuid4())
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding_np.tolist(),
                        payload=payload,
                    )
                ],
            )
            return True
        except Exception as e:
            self.logger.exception(f"Failed to enroll speaker, due to: {e}")
            return False

    def identify_speaker(self, data: np.ndarray, threshold: float) -> Union[str, None]:
        try:
            embedding_np = self._extract_embedding(data)

            search_results = self.client.query_points(
                collection_name=self.known_speakers,
                query=embedding_np.tolist(),
                with_payload=True,
                limit=1,
            )
            self.logger.info(f"Points: {search_results.points}")

            if search_results.points:
                top_result = search_results.points[0]
                found_speaker_id = top_result.payload.get("speaker_id")
                confidence = top_result.score

                if confidence >= threshold:
                    return found_speaker_id

            return None
        except Exception as e:
            self.logger.exception(f"Failed to identify speaker: {e}")
            return None

    def delete_speaker(self, speaker_id: str) -> bool:
        try:
            filter_query = {
                "must": [{"key": "speaker_id", "match": {"value": speaker_id}}]
            }

            points = self.client.scroll(
                collection_name=self.known_speakers,
                scroll_filter=filter_query,
                with_payload=False,
                with_vectors=False,
                limit=100,
            )

            point_ids = [point.id for point in points[0]]

            if not point_ids:
                return False

            self.client.delete(
                collection_name=self.known_speakers, points_selector=point_ids
            )
            return True
        except Exception:
            return False
