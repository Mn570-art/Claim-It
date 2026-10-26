"""Downloads for the claim draft. These files are not submitted anywhere."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.claims import get_claim
from app.api.serializers import checklist_out, claim_bundle, latest_draft_row
from app.core.database import get_db
from app.core.errors import AppError
from app.services.export_service import render_checklist_csv, render_json, render_pdf

router = APIRouter(prefix="/api/claims", tags=["exports"])


def _draft_or_404(claim):
    draft = latest_draft_row(claim)
    if draft is None:
        raise AppError(404, "draft_not_found", "Generate a draft before exporting.")
    return draft


@router.get("/{claim_id}/export/pdf")
def export_pdf(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = _draft_or_404(claim)
    payload = dict(draft.draft_json)
    claim_view = claim_bundle(claim)
    claim_view["reviewed_by_user"] = draft.reviewed_by_user
    claim_view["ready_for_submission"] = claim.status == "ready_for_submission"
    content = render_pdf(claim_view, payload)
    filename = f"{claim.claim_reference}-draft.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{claim_id}/export/json")
def export_json(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    draft = _draft_or_404(claim)
    bundle = claim_bundle(claim)
    bundle["export_note"] = "This file was prepared by Claim-It. It was not submitted to an insurer."
    bundle["draft_snapshot"] = draft.draft_json
    content = render_json(bundle)
    filename = f"{claim.claim_reference}-draft.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{claim_id}/export/checklist.csv")
def export_csv(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    if not claim.checklist_items:
        raise AppError(404, "checklist_not_found", "Run the checklist before exporting it.")
    content = render_checklist_csv([checklist_out(item) for item in claim.checklist_items])
    filename = f"{claim.claim_reference}-checklist.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
