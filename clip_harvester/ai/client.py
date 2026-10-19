"""Google GenAI client interface with Files API lifecycle management."""

import os
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from clip_harvester.ai.models import ChunkAnalysisResult
from clip_harvester.config import CONFIG


def check_api_key_present() -> bool:
    """Verifies that the GEMINI_API_KEY environment variable is set."""
    return bool(os.getenv("GEMINI_API_KEY"))


def create_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Instantiates a Google GenAI Client.

    Raises:
        ValueError: If no API key is found in environment or arguments.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please set it in your environment: $env:GEMINI_API_KEY='your-key'"
        )
    return genai.Client(api_key=key)


def upload_audio_and_wait(
    client: genai.Client,
    audio_path: Path,
    poll_interval: int = CONFIG.poll_interval_seconds,
    timeout: int = CONFIG.poll_timeout_seconds,
):
    """Uploads an audio file via the Files API and polls until it reaches ACTIVE state.

    Raises:
        TimeoutError: If file processing exceeds timeout.
        RuntimeError: If file processing fails remotely.
    """
    file_ref = client.files.upload(file=str(audio_path.resolve()))
    start_time = time.time()

    while True:
        file_ref = client.files.get(name=file_ref.name)
        state_name = getattr(file_ref.state, "name", str(file_ref.state))

        if state_name == "ACTIVE":
            return file_ref
        elif state_name == "FAILED":
            raise RuntimeError(f"Gemini remote file processing failed for: {audio_path.name}")

        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timed out waiting for file {audio_path.name} to become ACTIVE in Gemini API.")

        time.sleep(poll_interval)


def analyze_audio_chunk(
    client: genai.Client,
    audio_path: Path,
    prompt: str,
    model_name: str = CONFIG.default_model,
) -> ChunkAnalysisResult:
    """Uploads an audio chunk, generates structured clip analysis, and ensures remote file cleanup.

    Guarantees remote file deletion in a finally block to prevent quota leaks.
    """
    uploaded_file = None
    try:
        uploaded_file = upload_audio_and_wait(client, audio_path)

        response = client.models.generate_content(
            model=model_name,
            contents=[
                uploaded_file,
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChunkAnalysisResult,
                temperature=0.1,  # Low temperature for strict factual alignment
            ),
        )

        if response.parsed and isinstance(response.parsed, ChunkAnalysisResult):
            return response.parsed

        # Fallback parsing in case SDK returns text
        if response.text:
            return ChunkAnalysisResult.model_validate_json(response.text)

        raise RuntimeError("Empty response received from Gemini model.")

    finally:
        # Guarantee cleanup of remote media file
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass  # Ignore network errors on file deletion
