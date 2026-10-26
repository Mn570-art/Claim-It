"""Speech transcription and optional spoken playback."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.claims import get_claim
from app.api.serializers import claim_bundle, narrative_out
from app.core.database import get_db
from app.core.errors import AppError
from app.models.entities import IncidentNarrative, TranscriptCache, utcnow
from app.schemas.dto import NarrativeIn, SpeakIn
from app.services.sarvam_speech import audio_sha256, speak, transcribe

router = APIRouter(tags=["voice"])


@router.post("/api/claims/{claim_id}/transcribe")
async def transcribe_audio(
    claim_id: str,
    request: Request,
    language: str = Form("en"),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    claim = get_claim(db, claim_id)
    if language not in {"en", "hi"}:
        raise AppError(400, "validation_error", "language must be en or hi")
    content = await audio.read()
    if not content:
        raise AppError(400, "empty_file", "The recording was empty.")
    if len(content) > 15 * 1024 * 1024:
        raise AppError(400, "file_too_large", "Recordings are limited to 15 MB.")
    digest = audio_sha256(content)
    cached = (
        db.query(TranscriptCache)
        .filter(TranscriptCache.claim_id == claim.id, TranscriptCache.audio_sha256 == digest)
        .first()
    )
    if cached:
        return {
            "transcript": cached.transcript,
            "language_code": cached.language_code,
            "cached": True,
            "live_api_call": False,
            "engine": "cache",
        }
    if claim.demo_mode:
        raise AppError(
            409,
            "demo_mode",
            "Demo mode does not send audio to Sarvam. Type the incident, or load the fictional transcript.",
        )
    client = request.app.state.sarvam_client_factory()
    result = transcribe(client, content, audio.filename or "audio.webm", language)
    db.add(
        TranscriptCache(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            audio_sha256=digest,
            transcript=result["transcript"],
            language_code=result.get("language_code"),
        )
    )
    db.commit()
    result["cached"] = False
    return result


@router.post("/api/claims/{claim_id}/narrative")
def save_narrative(claim_id: str, body: NarrativeIn, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    text = (body.confirmed_transcript or body.transcript or "").strip()
    if body.confirm and not text:
        raise AppError(400, "empty_transcript", "Enter or record the incident before confirming it.")
    narrative = IncidentNarrative(
        id=str(uuid.uuid4()),
        claim_id=claim.id,
        transcript=body.transcript.strip(),
        confirmed_transcript=text if body.confirm else None,
        language=body.language,
        source="demo" if claim.demo_mode and body.source == "voice" else body.source,
        extracted_details_json={"confirmed": body.confirm},
    )
    db.add(narrative)
    claim.language = body.language
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(claim)
    return {"narrative": narrative_out(narrative), "claim": claim_bundle(claim)}


@router.post("/api/speech/speak")
def speak_text(body: SpeakIn, request: Request):
    if body.language not in {"en", "hi"}:
        raise AppError(400, "validation_error", "language must be en or hi")
    client = request.app.state.sarvam_client_factory()
    audio = speak(client, body.text, body.language)
    return Response(content=audio, media_type="audio/mpeg")
