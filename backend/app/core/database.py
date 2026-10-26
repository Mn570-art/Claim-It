"""SQLite setup. Tables are created on startup; see README for the schema."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def init_db(settings: Settings | None = None) -> None:
    global _engine, _SessionLocal
    settings = settings or get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    if settings.sqlalchemy_url.startswith("sqlite:///"):
        db_path = settings.sqlalchemy_url.removeprefix("sqlite:///")
        from pathlib import Path

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(
        settings.sqlalchemy_url,
        connect_args={"check_same_thread": False},
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    from app.models.entities import (  # noqa: F401
        AnalysisRun,
        ChecklistItem,
        Claim,
        ClaimDraft,
        CoverageFinding,
        Document,
        IncidentNarrative,
        PolicyChunk,
        Setting,
        TranscriptCache,
    )

    Base.metadata.create_all(_engine)


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
