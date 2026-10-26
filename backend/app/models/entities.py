"""Persistence model for claims, documents, narratives, findings, and drafts."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    claim_type: Mapped[str] = mapped_column(String(32), default="health")
    nickname: Mapped[str] = mapped_column(String(200), default="")
    policyholder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    insurer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    policy_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    incident_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    claim_type_detail: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    admission_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    discharge_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    narratives: Mapped[list["IncidentNarrative"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    findings: Mapped[list["CoverageFinding"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    drafts: Mapped[list["ClaimDraft"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    chunks: Mapped[list["PolicyChunk"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(300))
    document_type: Mapped[str] = mapped_column(String(40), default="other")
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="pending")
    processing_engine: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    live_api_call: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="documents")
    chunks: Mapped[list["PolicyChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class IncidentNarrative(Base):
    __tablename__ = "incident_narratives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    transcript: Mapped[str] = mapped_column(Text, default="")
    confirmed_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    source: Mapped[str] = mapped_column(String(20), default="text")
    extracted_details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="narratives")


class TranscriptCache(Base):
    __tablename__ = "transcript_cache"
    __table_args__ = (UniqueConstraint("claim_id", "audio_sha256", name="uq_transcript_audio"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    audio_sha256: Mapped[str] = mapped_column(String(64))
    transcript: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text)

    claim: Mapped[Claim] = relationship(back_populates="chunks")
    document: Mapped[Document] = relationship(back_populates="chunks")


class CoverageFinding(Base):
    __tablename__ = "coverage_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    explanation: Mapped[str] = mapped_column(Text)
    policy_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supporting_evidence_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_information_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_status: Mapped[str] = mapped_column(String(20), default="unverified")
    review_status: Mapped[str] = mapped_column(String(20), default="needs_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="findings")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="checklist_items")


class ClaimDraft(Base):
    __tablename__ = "claim_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    draft_json: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    reviewed_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="drafts")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    engine: Mapped[str] = mapped_column(String(40))
    live_api_call: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    follow_up_questions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    inconsistencies_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    financials_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_status: Mapped[str] = mapped_column(String(40), default="needs_review")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="analysis_runs")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
