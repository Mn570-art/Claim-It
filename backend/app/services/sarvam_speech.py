"""Saaras v4 speech-to-text and Bulbul v4 Flash text-to-speech."""

import base64
import hashlib
import io
import subprocess

from app.core.config import get_settings
from app.core.errors import AppError, MissingCredentialsError, SarvamTimeoutError
from app.services.sarvam_client import map_sarvam_error, request_options

LANGUAGE_CODES = {"en": "en-IN", "hi": "hi-IN", "en-IN": "en-IN", "hi-IN": "hi-IN", "unknown": "unknown"}
SPEAKERS = {"en-IN": "sanchita_en_insurance", "hi-IN": "ritu_hi_insurance"}


def language_code(value: str | None) -> str:
    if not value:
        return "unknown"
    return LANGUAGE_CODES.get(value, "unknown")


def audio_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def to_wav(content: bytes, filename: str) -> bytes:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in {"wav", "wave"} and content.startswith(b"RIFF"):
        return content
    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                "pipe:1",
            ],
            input=content,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(400, "audio_unreadable", "The recording took too long to convert. Try a shorter message or type it.") from exc
    if completed.returncode != 0 or not completed.stdout:
        raise AppError(400, "audio_unreadable", "The recording could not be read. Try again or type the description.")
    return completed.stdout


def transcribe(client, content: bytes, filename: str, language: str | None) -> dict:
    if client is None:
        raise MissingCredentialsError(
            "Speech transcription needs SARVAM_API_KEY. Nothing was sent to Sarvam. Type the incident instead, or use Demo Mode."
        )
    wav = to_wav(content, filename or "audio.webm")
    code = language_code(language)
    settings = get_settings()
    try:
        response = client.speech_to_text.transcribe(
            file=("audio.wav", io.BytesIO(wav), "audio/wav"),
            model="saaras:v4",
            mode="transcribe",
            language_code=code,
            input_audio_codec="wav",
            keyterms=["Claim-It", "reimbursement", "cashless", "discharge", "appendectomy"],
            request_options=request_options(settings.sarvam_timeout_seconds),
        )
    except MissingCredentialsError:
        raise
    except SarvamTimeoutError:
        raise
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    transcript = getattr(response, "transcript", None)
    if isinstance(response, dict):
        transcript = response.get("transcript")
    if not transcript or not str(transcript).strip():
        raise AppError(422, "empty_transcript", "Sarvam returned an empty transcript. Record again or type the description.")
    detected = getattr(response, "language_code", None)
    if isinstance(response, dict):
        detected = response.get("language_code")
    return {
        "transcript": str(transcript).strip(),
        "language_code": detected or (None if code == "unknown" else code),
        "live_api_call": True,
        "engine": "saaras:v4",
    }


def speak(client, text: str, language: str | None) -> bytes:
    if client is None:
        raise MissingCredentialsError(
            "Voice playback needs SARVAM_API_KEY. The written explanation is still available."
        )
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise AppError(400, "empty_text", "There is no text to read aloud.")
    cleaned = cleaned[:500]
    code = language_code(language)
    if code == "unknown":
        code = "en-IN"
    settings = get_settings()
    try:
        response = client.text_to_speech.convert(
            text=cleaned,
            language_code=code,
            model="bulbul:v4-flash",
            speaker=SPEAKERS.get(code, SPEAKERS["en-IN"]),
            output_audio_codec="mp3",
            pace=1.0,
            request_options=request_options(settings.sarvam_timeout_seconds),
        )
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    audios = getattr(response, "audios", None)
    if isinstance(response, dict):
        audios = response.get("audios")
    if not audios:
        raise AppError(502, "sarvam_error", "Sarvam did not return audio. The written text is unchanged.")
    try:
        return base64.b64decode(audios[0])
    except Exception as exc:
        raise AppError(502, "sarvam_error", "Sarvam returned audio that could not be read.") from exc
