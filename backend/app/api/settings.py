"""Language, voice playback, retention notice, and local data deletion."""

import shutil

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import Claim, Setting
from app.schemas.dto import SettingsPatch
from app.services.workflow import DISCLAIMER

router = APIRouter(prefix="/api", tags=["settings"])

DEFAULTS = {"preferred_language": "en", "voice_playback": "true"}


def _read(db: Session) -> dict:
    stored = {row.key: row.value for row in db.query(Setting).all()}
    language = stored.get("preferred_language", DEFAULTS["preferred_language"])
    playback = stored.get("voice_playback", DEFAULTS["voice_playback"]) == "true"
    settings = get_settings()
    return {
        "preferred_language": language if language in {"en", "hi"} else "en",
        "voice_playback": playback,
        "retention_days": settings.retention_days,
        "sarvam_configured": settings.sarvam_configured,
        "max_upload_mb": settings.max_upload_mb,
        "max_pdf_pages": settings.max_pdf_pages,
        "disclaimer": DISCLAIMER,
        "privacy": (
            "Documents stay on this computer. They are not given public links. "
            "The Sarvam API key, when set, stays in the server environment. "
            f"Claims older than {settings.retention_days} days are removed when the server starts. "
            "You can delete everything now."
        ),
    }


def _put(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    return _read(db)


@router.patch("/settings")
def update_settings(body: SettingsPatch, db: Session = Depends(get_db)):
    if body.preferred_language is not None:
        _put(db, "preferred_language", body.preferred_language)
    if body.voice_playback is not None:
        _put(db, "voice_playback", "true" if body.voice_playback else "false")
    db.commit()
    return _read(db)


@router.delete("/data")
def delete_all(db: Session = Depends(get_db)):
    settings = get_settings()
    for claim in db.query(Claim).all():
        db.delete(claim)
    db.query(Setting).delete()
    db.commit()
    if settings.upload_path.exists():
        shutil.rmtree(settings.upload_path, ignore_errors=True)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    return {"deleted": True}


def purge_expired(db: Session) -> int:
    from datetime import datetime, timedelta, timezone

    settings = get_settings()
    if settings.retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    removed = 0
    for claim in db.query(Claim).all():
        updated = claim.updated_at
        if updated is None:
            continue
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if updated < cutoff:
            folder = settings.upload_path / claim.id
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
            db.delete(claim)
            removed += 1
    if removed:
        db.commit()
    return removed
