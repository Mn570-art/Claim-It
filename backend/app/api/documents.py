"""Document upload, processing, and private file access."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.claims import get_claim
from app.api.serializers import document_out
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.entities import Document, utcnow
from app.services.files import safe_storage_path, validate_upload
from app.services.workflow import process_document

router = APIRouter(tags=["documents"])

DOCUMENT_TYPES = {
    "policy",
    "discharge_summary",
    "bill",
    "prescription",
    "diagnostic",
    "claim_form",
    "bank_proof",
    "other",
}


def get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise AppError(404, "document_not_found", "No document exists with that id.")
    return document


@router.post("/api/claims/{claim_id}/documents")
async def upload_document(
    claim_id: str,
    request: Request,
    document_type: str = Form("other"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if document_type not in DOCUMENT_TYPES:
        raise AppError(400, "validation_error", "Choose a document type from the list.")
    claim = get_claim(db, claim_id)
    settings = get_settings()
    content = await file.read()
    checked = validate_upload(file.filename or "", content, settings.max_upload_mb, settings.max_pdf_pages)
    document_id = str(uuid.uuid4())
    destination = safe_storage_path(settings.upload_path, claim.id, document_id, checked["filename"])
    destination.write_bytes(content)
    document = Document(
        id=document_id,
        claim_id=claim.id,
        original_filename=checked["filename"],
        document_type=document_type,
        storage_path=str(destination),
        mime_type=checked["mime_type"],
        size_bytes=checked["size_bytes"],
        page_count=checked["page_count"],
        processing_status="pending",
        live_api_call=False,
    )
    db.add(document)
    db.flush()
    client = None
    if not claim.demo_mode:
        client = request.app.state.sarvam_client_factory()
    process_document(db, document, claim, client=client)
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(document)
    return document_out(document)


@router.get("/api/claims/{claim_id}/documents")
def list_documents(claim_id: str, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    return {"documents": [document_out(document) for document in claim.documents]}


@router.get("/api/documents/{document_id}")
def read_document(document_id: str, db: Session = Depends(get_db)):
    return document_out(get_document(db, document_id))


@router.delete("/api/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = get_document(db, document_id)
    claim = get_claim(db, document.claim_id)
    path = Path(document.storage_path)
    if path.exists():
        path.unlink()
    db.delete(document)
    remaining = [item for item in claim.documents if item.id != document.id]
    if not remaining:
        claim.status = "draft"
    claim.updated_at = utcnow()
    db.commit()
    return {"deleted": True, "id": document_id}


@router.post("/api/documents/{document_id}/process")
def reprocess(document_id: str, request: Request, db: Session = Depends(get_db)):
    document = get_document(db, document_id)
    claim = get_claim(db, document.claim_id)
    document.processing_status = "processing"
    document.error_message = None
    db.flush()
    client = None if claim.demo_mode else request.app.state.sarvam_client_factory()
    process_document(db, document, claim, client=client)
    claim.updated_at = utcnow()
    db.commit()
    db.refresh(document)
    return document_out(document)


@router.get("/api/documents/{document_id}/file")
def document_file(document_id: str, db: Session = Depends(get_db)):
    document = get_document(db, document_id)
    path = Path(document.storage_path).resolve()
    root = get_settings().upload_path.resolve()
    if not str(path).startswith(str(root)):
        raise AppError(400, "invalid_path", "That file path is not allowed.")
    if not path.exists():
        raise AppError(404, "file_missing", "The file is no longer available.")
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.original_filename,
        content_disposition_type="inline",
    )
