"""Claim CRUD and the fictional demo seed."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.serializers import claim_bundle, claim_summary
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.entities import Claim, utcnow
from app.schemas.dto import ClaimCreate, ClaimPatch
from app.services.demo import attach_samples, seed_demo

router = APIRouter(prefix="/api/claims", tags=["claims"])


def get_claim(db: Session, claim_id: str) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise AppError(404, "claim_not_found", "No claim exists with that id.")
    return claim


def _reference(db: Session) -> str:
    for _ in range(5):
        reference = "CLM-" + uuid.uuid4().hex[:6].upper()
        if db.query(Claim).filter(Claim.claim_reference == reference).first() is None:
            return reference
    return "CLM-" + uuid.uuid4().hex[:10].upper()


@router.post("")
def create_claim(body: ClaimCreate, db: Session = Depends(get_db)):
    if body.claim_type == "motor":
        raise AppError(400, "not_in_this_version", "Motor insurance is shown as a future feature. Start a health claim.")
    claim = Claim(
        id=str(uuid.uuid4()),
        claim_reference=_reference(db),
        claim_type="health",
        nickname=body.nickname or "Health claim",
        policyholder_name=body.policyholder_name,
        insurer_name=body.insurer_name,
        policy_number=body.policy_number,
        incident_date=body.incident_date,
        claim_type_detail=body.claim_type_detail,
        language=body.language,
        status="draft",
        demo_mode=False,
        patient_name=body.patient_name,
        hospital_name=body.hospital_name,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


@router.get("")
def list_claims(db: Session = Depends(get_db)):
    claims = db.query(Claim).order_by(Claim.updated_at.desc()).all()
    return {"claims": [claim_summary(claim) for claim in claims]}


@router.get("/{claim_id}")
def read_claim(claim_id: str, db: Session = Depends(get_db)):
    return claim_bundle(get_claim(db, claim_id))


@router.patch("/{claim_id}")
def update_claim(claim_id: str, body: ClaimPatch, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("claim_type") == "motor":
        raise AppError(400, "not_in_this_version", "Motor insurance is a future feature.")
    for key, value in data.items():
        setattr(claim, key, value)
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


@router.delete("/{claim_id}")
def delete_claim(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    folder = get_settings().upload_path / claim.id
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    db.delete(claim)
    db.commit()
    return {"deleted": True, "id": claim_id}


@router.post("/{claim_id}/demo-documents")
def demo_documents(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    claim.demo_mode = True
    claim.nickname = claim.nickname or "Father's hospitalisation — fictional"
    if not claim.policyholder_name:
        claim.policyholder_name = "Ananya Sharma"
    if not claim.patient_name:
        claim.patient_name = "Harish Sharma"
    if not claim.insurer_name:
        claim.insurer_name = "Narmada Health Assurance"
    if not claim.incident_date:
        claim.incident_date = "2026-10-12"
    if not claim.claim_type_detail:
        claim.claim_type_detail = "reimbursement"
    attach_samples(db, claim)
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


demo_router = APIRouter(prefix="/api/demo", tags=["demo"])


@demo_router.post("/seed")
def seed(language: str = "en", stage: str = "ready", db: Session = Depends(get_db)):
    if language not in {"en", "hi"}:
        raise AppError(400, "validation_error", "language must be en or hi")
    if stage not in {"details", "documents", "narrative", "analysis", "ready"}:
        raise AppError(400, "validation_error", "stage is not recognised")
    claim = seed_demo(db, language=language, stage=stage)
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


@demo_router.get("/samples")
def samples():
    from app.services.demo import sample_paths

    paths = sample_paths()
    return {
        "fictional": True,
        "files": [
            {"key": key, "filename": path.name, "url": f"/api/demo/samples/{key}"}
            for key, path in paths.items()
        ],
    }


@demo_router.get("/samples/{key}")
def sample_file(key: str):
    from fastapi.responses import FileResponse

    from app.services.demo import sample_paths

    paths = sample_paths()
    if key not in paths:
        raise AppError(404, "sample_not_found", "That sample file does not exist.")
    path = paths[key]
    return FileResponse(path, media_type="application/pdf", filename=path.name)
