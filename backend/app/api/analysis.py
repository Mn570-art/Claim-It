"""Policy analysis, checklist, draft editing, and questions."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.claims import get_claim
from app.api.serializers import analysis_out, checklist_out, claim_bundle, draft_out, finding_out, latest_draft_row, latest_run
from app.core.database import get_db
from app.core.errors import AppError
from app.models.entities import utcnow
from app.schemas.dto import ConfirmIn, DraftPatch, QuestionIn
from app.services.workflow import DISCLAIMER, answer, generate_draft, recalculate_draft, run_analysis

router = APIRouter(prefix="/api/claims", tags=["analysis"])


def _client(request: Request, claim):
    if claim.demo_mode:
        return None
    return request.app.state.sarvam_client_factory()


@router.post("/{claim_id}/analyze")
def analyze(claim_id: str, request: Request, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    run_analysis(db, claim, client=_client(request, claim))
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


@router.get("/{claim_id}/findings")
def findings(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    return {"findings": [finding_out(item) for item in claim.findings], "analysis": analysis_out(latest_run(claim))}


@router.post("/{claim_id}/checklist")
def checklist(claim_id: str, request: Request, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    if not claim.checklist_items:
        run_analysis(db, claim, client=_client(request, claim))
        db.commit()
        db.refresh(claim)
    return {"checklist": [checklist_out(item) for item in claim.checklist_items]}


@router.post("/{claim_id}/draft")
def create_draft(claim_id: str, request: Request, regenerate: bool = False, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = generate_draft(db, claim, regenerate=regenerate, client=_client(request, claim))
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.get("/{claim_id}/draft")
def read_draft(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before opening it.")
    return draft_out(draft)


@router.patch("/{claim_id}/draft")
def patch_draft(claim_id: str, body: DraftPatch, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before editing it.")
    payload = dict(draft.draft_json or {})
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        payload[key] = value
    payload["warning"] = DISCLAIMER
    draft.draft_json = payload
    flag_modified(draft, "draft_json")
    draft.version += 1
    draft.reviewed_by_user = False
    draft.user_confirmed = False
    if claim.status == "ready_for_submission":
        claim.status = "needs_user_review"
    draft.updated_at = utcnow()
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.post("/{claim_id}/recalculate")
def recalculate(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before recalculating.")
    recalculate_draft(claim, draft)
    flag_modified(draft, "draft_json")
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.post("/{claim_id}/draft/review")
def review_draft(claim_id: str, body: ConfirmIn, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before marking it reviewed.")
    if not body.confirmed:
        raise AppError(400, "confirmation_required", "Confirm that you have checked the draft before marking it reviewed.")
    draft.reviewed_by_user = True
    draft.user_confirmed = True
    claim.status = "needs_user_review"
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(claim)
    return claim_bundle(claim)


@router.post("/{claim_id}/ready")
def mark_ready(claim_id: str, body: ConfirmIn, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before marking it ready.")
    if not body.confirmed:
        raise AppError(400, "confirmation_required", "Confirm the declaration before marking the draft ready for external submission.")
    if not draft.reviewed_by_user:
        raise AppError(400, "review_required", "Mark the draft as reviewed before marking it ready. Nothing is sent to an insurer.")
    draft.user_confirmed = True
    claim.status = "ready_for_submission"
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(claim)
    return {
        **claim_bundle(claim),
        "notice": "Marked ready for you to submit outside Claim-It. Nothing was sent to an insurer.",
    }


@router.post("/{claim_id}/ask")
def ask(claim_id: str, body: QuestionIn, request: Request, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    return answer(claim, body.question, client=_client(request, claim))
