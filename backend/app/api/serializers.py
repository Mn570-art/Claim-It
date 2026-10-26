"""API shapes. Storage paths and page caches stay on the server."""

from app.models.entities import AnalysisRun, ChecklistItem, Claim, ClaimDraft, CoverageFinding, Document, IncidentNarrative


def document_out(document: Document) -> dict:
    payload = document.extracted_fields_json or {}
    return {
        "id": document.id,
        "claim_id": document.claim_id,
        "original_filename": document.original_filename,
        "document_type": document.document_type,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "page_count": document.page_count,
        "processing_status": document.processing_status,
        "processing_engine": document.processing_engine,
        "live_api_call": document.live_api_call,
        "error_message": document.error_message,
        "job_id": document.job_id,
        "extracted_fields": payload.get("fields") or [],
        "line_items": payload.get("line_items") or [],
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
        "file_path": f"/api/documents/{document.id}/file",
    }


def narrative_out(item: IncidentNarrative | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "transcript": item.transcript,
        "confirmed_transcript": item.confirmed_transcript,
        "language": item.language,
        "source": item.source,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def finding_out(item: CoverageFinding) -> dict:
    return {
        "id": item.id,
        "category": item.category,
        "title": item.title,
        "explanation": item.explanation,
        "policy_clause": item.policy_clause,
        "policy_source": item.policy_source,
        "source_document_id": item.source_document_id,
        "source_page": item.source_page,
        "claim_evidence": item.supporting_evidence_json or [],
        "missing_information": item.missing_information_json or [],
        "recommended_next_step": item.recommended_next_step,
        "citation_status": item.citation_status,
        "review_status": item.review_status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def checklist_out(item: ChecklistItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "reason": item.reason,
        "status": item.status,
        "source": item.source,
        "source_reference": item.source_reference,
        "document_id": item.document_id,
    }


def draft_out(item: ClaimDraft | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "version": item.version,
        "reviewed_by_user": item.reviewed_by_user,
        "user_confirmed": item.user_confirmed,
        "draft": item.draft_json,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def analysis_out(item: AnalysisRun | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "engine": item.engine,
        "live_api_call": item.live_api_call,
        "summary": item.summary,
        "follow_up_questions": item.follow_up_questions_json or [],
        "inconsistencies": item.inconsistencies_json or [],
        "financials": item.financials_json or {},
        "overall_status": item.overall_status,
        "note": item.note,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def claim_summary(claim: Claim) -> dict:
    return {
        "id": claim.id,
        "claim_reference": claim.claim_reference,
        "claim_type": claim.claim_type,
        "nickname": claim.nickname,
        "policyholder_name": claim.policyholder_name,
        "insurer_name": claim.insurer_name,
        "policy_number": claim.policy_number,
        "incident_date": claim.incident_date,
        "claim_type_detail": claim.claim_type_detail,
        "language": claim.language,
        "status": claim.status,
        "demo_mode": claim.demo_mode,
        "patient_name": claim.patient_name,
        "hospital_name": claim.hospital_name,
        "admission_date": claim.admission_date,
        "discharge_date": claim.discharge_date,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
    }


def latest_narrative(claim: Claim) -> IncidentNarrative | None:
    if not claim.narratives:
        return None
    return sorted(claim.narratives, key=lambda item: item.created_at)[-1]


def latest_run(claim: Claim) -> AnalysisRun | None:
    if not claim.analysis_runs:
        return None
    return sorted(claim.analysis_runs, key=lambda item: item.created_at)[-1]


def latest_draft_row(claim: Claim) -> ClaimDraft | None:
    if not claim.drafts:
        return None
    return sorted(claim.drafts, key=lambda item: item.version)[-1]


def claim_bundle(claim: Claim) -> dict:
    return {
        **claim_summary(claim),
        "documents": [document_out(document) for document in sorted(claim.documents, key=lambda item: item.uploaded_at or item.id)],
        "narrative": narrative_out(latest_narrative(claim)),
        "findings": [finding_out(item) for item in claim.findings],
        "checklist": [checklist_out(item) for item in claim.checklist_items],
        "draft": draft_out(latest_draft_row(claim)),
        "analysis": analysis_out(latest_run(claim)),
    }
