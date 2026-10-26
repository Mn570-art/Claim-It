"""Seed a fictional claim. This path never calls Sarvam."""

import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Claim, Document, IncidentNarrative, utcnow
from app.services.files import safe_storage_path
from app.services.sample_corpus import NARRATIVE_EN, NARRATIVE_HI
from app.services.sample_docs import SAMPLE_FILES, ensure_sample_documents
from app.services.workflow import generate_draft, process_document, run_analysis

SAMPLE_TYPES = {
    "policy": "policy",
    "discharge": "discharge_summary",
    "bill": "bill",
    "pharmacy": "bill",
}


def sample_paths() -> dict[str, Path]:
    return ensure_sample_documents(get_settings().sample_path)


def attach_samples(db: Session, claim: Claim) -> None:
    paths = sample_paths()
    for key, path in paths.items():
        content = path.read_bytes()
        document_id = str(uuid.uuid4())
        destination = safe_storage_path(get_settings().upload_path, claim.id, document_id, path.name)
        shutil.copyfile(path, destination)
        document = Document(
            id=document_id,
            claim_id=claim.id,
            original_filename=SAMPLE_FILES[key],
            document_type=SAMPLE_TYPES[key],
            storage_path=str(destination),
            mime_type="application/pdf",
            size_bytes=len(content),
            page_count=None,
            processing_status="pending",
            live_api_call=False,
        )
        db.add(document)
        db.flush()
        process_document(db, document, claim, client=None, force_local=True)


def seed_demo(db: Session, language: str = "en", stage: str = "ready") -> Claim:
    claim = Claim(
        id=str(uuid.uuid4()),
        claim_reference="CLM-" + uuid.uuid4().hex[:6].upper(),
        claim_type="health",
        nickname="Father's hospitalisation — fictional",
        policyholder_name="Ananya Sharma",
        insurer_name="Narmada Health Assurance",
        policy_number=None,
        incident_date="2026-10-12",
        claim_type_detail="reimbursement",
        language="hi" if language == "hi" else "en",
        status="draft",
        demo_mode=True,
        patient_name="Harish Sharma",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(claim)
    db.flush()
    if stage == "details":
        return claim
    attach_samples(db, claim)
    narrative = NARRATIVE_HI if claim.language == "hi" else NARRATIVE_EN
    if stage == "documents":
        return claim
    db.add(
        IncidentNarrative(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            transcript=narrative,
            confirmed_transcript=narrative,
            language=claim.language,
            source="demo",
            extracted_details_json={"origin": "fictional sample narrative"},
        )
    )
    db.flush()
    if stage == "narrative":
        return claim
    run_analysis(db, claim, client=None)
    if stage == "analysis":
        return claim
    generate_draft(db, claim, regenerate=True, client=None)
    return claim
