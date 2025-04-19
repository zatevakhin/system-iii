import os
import uuid
import click
import numpy as np
import soundfile as sf
import torch
from pyannote.audio import Model
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


class SpeakerRecognizer:
    def __init__(self, host="localhost", grpc_port=6334, collection_name="speaker_embeddings", hf_token=None):
        self.client = QdrantClient(host=host, grpc_port=grpc_port, prefer_grpc=True)
        self.collection_name = collection_name
        self.embedding_size = 512
        self._initialize_collection()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        click.echo(f"Loading model on {device}...")

        self.model = Model.from_pretrained("pyannote/embedding", use_auth_token=hf_token)
        self.model.eval()
        self.device = device
        self.model = self.model.to(device)

    def _initialize_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size, distance=Distance.COSINE
                    ),
                )
                click.echo(f"Created collection '{self.collection_name}' in Qdrant")
            else:
                click.echo(f"Collection '{self.collection_name}' already exists in Qdrant")
        except Exception as e:
            click.echo(f"Failed to initialize Qdrant collection: {str(e)}")

    def process_audio(self, audio_file_path):
        audio_data, sample_rate = sf.read(audio_file_path)

        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]

        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32768).astype(np.int16)

        waveform = torch.tensor(audio_data, dtype=torch.float32) / 32768.0
        waveform = waveform.unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model(waveform)

        return embedding.cpu().numpy().flatten()

    def identify_speaker(self, audio_file_path, threshold=0.25):
        embedding_np = self.process_audio(audio_file_path)

        search_results = self.client.query_points(
            collection_name=self.collection_name,
            query=embedding_np.tolist(),
            with_payload=True,
            limit=1,
        )

        if search_results.points:
            top_result = search_results.points[0]
            found_speaker_id = top_result.payload.get("speaker_id")
            confidence = top_result.score

            if confidence >= threshold:
                return found_speaker_id, confidence

        return None, 0.0

    def add_speaker(self, audio_file_path, speaker_id):
        embedding_np = self.process_audio(audio_file_path)
        if np.isnan(embedding_np).any() or np.isinf(embedding_np).any():
            raise ValueError("Generated embedding contains NaN or inf values")

        point_id = str(uuid.uuid4())
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding_np.tolist(),
                    payload={"speaker_id": speaker_id}
                )
            ]
        )
        return point_id


@click.group()
def cli():
    """Speaker recognition tool for enrolling users and identifying speakers."""
    pass


@cli.command()
@click.argument('folder', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--speaker-id', '-s', required=True, help='ID for the speaker to enroll')
@click.option('--host', default='localhost', help='Qdrant server host')
@click.option('--port', default=6334, help='Qdrant server gRPC port')
@click.option('--hf-token', help='HuggingFace token for model access')
def enroll(folder, speaker_id, host, port, hf_token):
    """Enroll a speaker using all audio files in the specified folder."""
    recognizer = SpeakerRecognizer(host=host, grpc_port=port, hf_token=hf_token)

    audio_files = [f for f in os.listdir(folder) if f.endswith(('.wav', '.mp3', '.flac'))]

    if not audio_files:
        click.echo(f"No audio files found in {folder}")
        return

    success_count = 0
    for audio_file in audio_files:
        audio_path = os.path.join(folder, audio_file)
        try:
            point_id = recognizer.add_speaker(audio_path, speaker_id)
            success_count += 1
            click.echo(f"✓ Enrolled {audio_file}")
        except Exception as e:
            click.echo(f"✗ Error processing {audio_file}: {e}")

    click.echo(f"Successfully enrolled {success_count}/{len(audio_files)} files for speaker '{speaker_id}'")


@cli.command()
@click.argument('audio_file', type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--threshold', '-t', default=0.25, help='Confidence threshold (0-1)')
@click.option('--host', default='localhost', help='Qdrant server host')
@click.option('--port', default=6334, help='Qdrant server gRPC port')
@click.option('--hf-token', help='HuggingFace token for model access')
def identify(audio_file, threshold, host, port, hf_token):
    """Identify a speaker from a single audio file."""
    recognizer = SpeakerRecognizer(host=host, grpc_port=port, hf_token=hf_token)

    try:
        speaker_id, confidence = recognizer.identify_speaker(audio_file, threshold=threshold)
        if speaker_id:
            click.echo(f"Speaker identified: {speaker_id} with confidence {confidence:.3f}")
        else:
            click.echo(f"No speaker identified (below threshold {threshold})")
    except Exception as e:
        click.echo(f"Error processing {audio_file}: {e}")


@cli.command()
@click.argument('folder', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--threshold', '-t', default=0.25, help='Confidence threshold (0-1)')
@click.option('--host', default='localhost', help='Qdrant server host')
@click.option('--port', default=6334, help='Qdrant server gRPC port')
@click.option('--hf-token', help='HuggingFace token for model access')
def identify_batch(folder, threshold, host, port, hf_token):
    """Identify speakers from a folder of audio files and show results summary."""
    recognizer = SpeakerRecognizer(host=host, grpc_port=port, hf_token=hf_token)

    audio_files = [f for f in os.listdir(folder) if f.endswith(('.wav', '.mp3', '.flac'))]

    if not audio_files:
        click.echo(f"No audio files found in {folder}")
        return

    results = {}
    processed = 0

    with click.progressbar(audio_files, label='Processing audio files') as bar:
        for audio_file in bar:
            audio_path = os.path.join(folder, audio_file)
            try:
                speaker_id, confidence = recognizer.identify_speaker(audio_path, threshold=threshold)
                if speaker_id:
                    results[speaker_id] = results.get(speaker_id, 0) + 1
                processed += 1
            except Exception:
                continue

    click.echo("\nResults summary:")
    if not results:
        click.echo("No speakers identified in any files.")
    else:
        total_identified = sum(results.values())
        click.echo(f"Identified speakers in {total_identified}/{processed} files:")

        for speaker, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / processed) * 100
            click.echo(f"  {speaker}: {count} files ({percentage:.1f}%)")


if __name__ == "__main__":
    cli()

