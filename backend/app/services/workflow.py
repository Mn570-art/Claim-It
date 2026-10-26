"""Claim processing, analysis, checklist, and draft orchestration."""

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors import AppError, InvalidModelOutputError, SarvamJobError, SarvamTimeoutError
from app.models.entities import (
    AnalysisRun,
    ChecklistItem,
    Claim,
    ClaimDraft,
    CoverageFinding,
    Document,
    PolicyChunk,
    utcnow,
)
from app.services.calculations import D, build_financials, duplicate_bill_numbers
from app.services.checklist import build_checklist
from app.services.citations import bind_citation
from app.services.extraction import extract_fields, field_value, apply_external_values
from app.services.files import extract_pdf_pages
from app.services.findings import build_deterministic_findings, follow_up_questions, summary_text
from app.services.inconsistencies import build_inconsistencies, compare_names
from app.services.retrieval import chunk_pages, retrieve
from app.services.sarvam_chat import analysis_messages, answer_question, complete_json, model_to_findings
from app.services.sarvam_vision import digitise, extract
from app.services.textutil import normalize_match

DISCLAIMER = (
    "Claim-It provides AI-assisted document analysis and claim preparation for informational purposes. "
    "It does not determine official coverage, guarantee reimbursement, or replace advice from your insurer. "
    "Please verify all extracted information and policy interpretations before submitting a claim."
)

COPY_FIELDS = {
    "insurer_name": "insurer_name",
    "policy_number": "policy_number",
    "policyholder_name": "policyholder_name",
    "patient_name": "patient_name",
    "hospital_name": "hospital_name",
    "admission_date": "admission_date",
    "discharge_date": "discharge_date",
}


def _pages_from_document(document: Document) -> list[dict]:
    payload = document.extracted_fields_json or {}
    pages = payload.get("pages")
    if isinstance(pages, list) and pages:
        return pages
    path = Path(document.storage_path)
    if path.exists() and document.mime_type == "application/pdf":
        return extract_pdf_pages(path.read_bytes())
    return []


def _replace_chunks(db: Session, document: Document, pages: list[dict]) -> None:
    db.query(PolicyChunk).filter(PolicyChunk.document_id == document.id).delete(synchronize_session=False)
    if document.document_type != "policy":
        return
    for chunk in chunk_pages(pages, document.claim_id, document.id):
        db.add(
            PolicyChunk(
                id=chunk["id"],
                claim_id=chunk["claim_id"],
                document_id=chunk["document_id"],
                page_number=chunk["page_number"],
                section_title=chunk["section_title"],
                text=chunk["text"],
            )
        )


def _fill_claim(claim: Claim, payload: dict) -> None:
    for source, target in COPY_FIELDS.items():
        if getattr(claim, target):
            continue
        value = field_value(payload, source)
        if value:
            setattr(claim, target, value)
    if not claim.incident_date and claim.admission_date:
        claim.incident_date = claim.admission_date


def process_document(db: Session, document: Document, claim: Claim, client=None, sleeper=None, force_local: bool = False) -> Document:
    path = Path(document.storage_path)
    if not path.exists():
        raise AppError(404, "file_missing", "The uploaded file is no longer on disk.")
    content = path.read_bytes()
    local_pages: list[dict] = []
    if document.mime_type == "application/pdf":
        try:
            local_pages = extract_pdf_pages(content)
        except AppError:
            local_pages = []
    text_length = sum(len((page.get("text") or "").strip()) for page in local_pages)
    pages = list(local_pages)
    use_remote = client is not None and not claim.demo_mode and not force_local
    extracted = None
    error = None
    job_id = None
    live = False
    partial = False
    engine = "demo" if claim.demo_mode else "local_text"

    if use_remote:
        live = True
        try:
            if document.mime_type != "application/pdf" or text_length < 200:
                digit = digitise(
                    client,
                    document.original_filename,
                    content,
                    document.mime_type,
                    claim.language,
                    sleeper=sleeper or __import__("time").sleep,
                )
                job_id = digit["job_id"]
                partial = digit["status"] == "partially_completed"
                if digit["pages"]:
                    pages = digit["pages"]
            extracted_job = extract(
                client,
                document.original_filename,
                content,
                document.mime_type,
                document.document_type,
                sleeper=sleeper or __import__("time").sleep,
            )
            job_id = extracted_job["job_id"]
            partial = partial or extracted_job["status"] == "partially_completed"
            extracted = apply_external_values(
                pages,
                document.document_type,
                document.id,
                document.original_filename,
                extracted_job["result"],
                extracted_job["annotations"],
            )
            engine = "sarvam_vision"
        except (SarvamTimeoutError, SarvamJobError, AppError) as exc:
            if any((page.get("text") or "").strip() for page in pages):
                extracted = extract_fields(pages, document.document_type, document.id, document.original_filename)
                engine = "local_text"
                error = exc.message + " Local text extraction was saved instead."
            else:
                document.processing_status = "rejected" if isinstance(exc, SarvamJobError) and exc.details.get("job_status") == "rejected" else "failed"
                document.processing_engine = "sarvam_vision"
                document.live_api_call = True
                document.job_id = job_id
                document.error_message = exc.message
                document.extracted_fields_json = {"fields": [], "line_items": [], "pages": []}
                document.extracted_text = ""
                return document

    if extracted is None:
        if not any((page.get("text") or "").strip() for page in pages):
            document.processing_status = "failed"
            document.processing_engine = "demo" if claim.demo_mode else "local_text"
            document.live_api_call = False
            if claim.demo_mode:
                document.error_message = "This fictional file has no readable text."
            elif client is None:
                document.error_message = "This file has no extractable text. Sarvam Vision was not called because SARVAM_API_KEY is not configured."
            else:
                document.error_message = "This file has no extractable text."
            document.extracted_fields_json = {"fields": [], "line_items": [], "pages": []}
            document.extracted_text = ""
            return document
        extracted = extract_fields(pages, document.document_type, document.id, document.original_filename)
        engine = "demo" if claim.demo_mode else "local_text"

    document.extracted_fields_json = {**extracted, "pages": pages}
    document.extracted_text = "\n\n".join(
        f"--- page {page['page_number']} ---\n{page.get('text') or ''}" for page in pages
    )
    document.processing_status = "partially_completed" if partial and engine == "sarvam_vision" else "completed"
    document.processing_engine = engine
    document.live_api_call = bool(live and engine == "sarvam_vision")
    document.job_id = job_id
    document.error_message = error
    if pages:
        document.page_count = max(int(page["page_number"]) for page in pages)
    _replace_chunks(db, document, pages)
    _fill_claim(claim, extracted)
    if claim.status == "draft":
        claim.status = "documents_uploaded"
    claim.updated_at = utcnow()
    return document


def _narrative(claim: Claim) -> str:
    confirmed = [item for item in claim.narratives if item.confirmed_transcript]
    if not confirmed:
        return ""
    confirmed.sort(key=lambda item: item.created_at)
    return confirmed[-1].confirmed_transcript or ""


def _load_chunks(claim: Claim) -> list[dict]:
    return [
        {
            "id": chunk.id,
            "claim_id": chunk.claim_id,
            "document_id": chunk.document_id,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
            "text": chunk.text,
        }
        for chunk in claim.chunks
    ]


def gather_facts(claim: Claim) -> dict:
    facts = {
        "policyholder_name": claim.policyholder_name,
        "insurer_name": claim.insurer_name,
        "policy_number": claim.policy_number,
        "incident_date": claim.incident_date,
        "claim_type_detail": claim.claim_type_detail,
        "patient_name": claim.patient_name,
        "hospital_name": claim.hospital_name,
        "admission_date": claim.admission_date,
        "discharge_date": claim.discharge_date,
        "diagnosis": None,
        "procedure": None,
        "treatment": None,
        "bill_status": None,
        "coverage_start": None,
        "coverage_end": None,
        "deductible": None,
        "copayment": None,
        "room_rent_limit": None,
        "line_items": [],
        "printed_totals": [],
        "amount_paid": None,
        "bill_records": [],
        "has_bank_proof": False,
        "policy_uploaded": False,
        "narrative": _narrative(claim),
        "bill_patient_name": None,
        "discharge_patient_name": None,
    }
    for document in claim.documents:
        if document.document_type == "policy":
            facts["policy_uploaded"] = True
        if document.document_type == "bank_proof" and document.processing_status in {"completed", "partially_completed"}:
            facts["has_bank_proof"] = True
        if document.processing_status not in {"completed", "partially_completed"}:
            continue
        payload = document.extracted_fields_json or {}
        for key in (
            "policyholder_name",
            "insurer_name",
            "policy_number",
            "hospital_name",
            "admission_date",
            "discharge_date",
            "diagnosis",
            "procedure",
            "treatment",
            "bill_status",
            "coverage_start",
            "coverage_end",
            "deductible",
            "copayment",
            "room_rent_limit",
        ):
            value = field_value(payload, key)
            if value and not facts.get(key):
                facts[key] = value
        patient = field_value(payload, "patient_name")
        if patient and document.document_type == "bill" and not facts["bill_patient_name"]:
            facts["bill_patient_name"] = patient
        if patient and document.document_type == "discharge_summary":
            facts["discharge_patient_name"] = patient
        if patient and not facts["patient_name"]:
            facts["patient_name"] = patient
        printed = field_value(payload, "printed_total")
        if printed:
            parsed = D(printed)
            if parsed is not None:
                facts["printed_totals"].append(parsed)
        paid = field_value(payload, "amount_paid")
        if paid and facts["amount_paid"] is None:
            facts["amount_paid"] = D(paid)
        bill_number = field_value(payload, "bill_number")
        if bill_number:
            facts["bill_records"].append(
                {
                    "bill_number": bill_number,
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "amount": field_value(payload, "printed_total") or field_value(payload, "amount"),
                    "description": field_value(payload, "description") or document.original_filename,
                }
            )
        for item in payload.get("line_items") or []:
            row = dict(item)
            row["bill_number"] = bill_number
            row["document_id"] = document.id
            row["filename"] = document.original_filename
            facts["line_items"].append(row)
    if not facts["incident_date"]:
        facts["incident_date"] = facts.get("admission_date")
    return facts


def _financials_for(facts: dict, amount_claimed: str | None = None) -> dict:
    return build_financials(
        items=facts["line_items"],
        printed_totals=facts["printed_totals"],
        amount_paid=facts["amount_paid"],
        amount_claimed=D(amount_claimed) if amount_claimed else None,
        room_limit_text=facts.get("room_rent_limit"),
        deductible_text=facts.get("deductible"),
        copay_text=facts.get("copayment"),
        duplicates=duplicate_bill_numbers(facts["bill_records"]),
    )


def _document_rows(claim: Claim) -> list[dict]:
    return [
        {
            "id": document.id,
            "document_type": document.document_type,
            "processing_status": document.processing_status,
            "original_filename": document.original_filename,
        }
        for document in claim.documents
    ]


def _save_findings(db: Session, claim: Claim, findings: list[dict]) -> None:
    db.query(CoverageFinding).filter(CoverageFinding.claim_id == claim.id).delete()
    for finding in findings:
        db.add(
            CoverageFinding(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                category=finding["category"],
                title=finding["title"],
                explanation=finding["explanation"],
                policy_clause=finding.get("policy_clause"),
                policy_source=finding.get("policy_source"),
                source_document_id=finding.get("source_document_id"),
                source_page=finding.get("source_page"),
                supporting_evidence_json=finding.get("supporting_evidence") or [],
                missing_information_json=finding.get("missing_information") or [],
                recommended_next_step=finding.get("recommended_next_step"),
                citation_status=finding.get("citation_status") or "none",
                review_status=finding.get("review_status") or "needs_review",
            )
        )


def _save_checklist(db: Session, claim: Claim, items: list[dict]) -> None:
    db.query(ChecklistItem).filter(ChecklistItem.claim_id == claim.id).delete()
    for item in items:
        db.add(
            ChecklistItem(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                name=item["name"],
                reason=item["reason"],
                status=item["status"],
                source=item["source"],
                source_reference=item.get("source_reference"),
                document_id=item.get("document_id"),
            )
        )


def reconcile(model_findings: list[dict], chunks: list[dict], deterministic: list[dict]) -> list[dict]:
    cleaned = [bind_citation(finding, chunks) for finding in model_findings]
    quoted = {normalize_match(item.get("policy_clause") or "") for item in cleaned if item.get("policy_clause")}
    for finding in deterministic:
        clause = normalize_match(finding.get("policy_clause") or "")
        if finding["code"] == "bill_total" and not any(item["code"] == "bill_total" for item in cleaned):
            cleaned.append(finding)
            continue
        if clause and clause not in quoted and finding["code"] in {"hospitalization", "room_rent", "consumables", "bank_proof", "waiting_period"}:
            cleaned.append(finding)
            quoted.add(clause)
    verified_or_missing = [item for item in cleaned if item.get("title")]
    return verified_or_missing or deterministic


def run_analysis(db: Session, claim: Claim, client=None) -> AnalysisRun:
    if claim.claim_type == "motor":
        raise AppError(400, "not_in_this_version", "Motor insurance is a labelled future feature. Create a health claim to continue.")
    facts = gather_facts(claim)
    chunks = _load_chunks(claim)
    financials = _financials_for(facts)
    inconsistencies = build_inconsistencies(facts, financials)
    name_review = compare_names(facts.get("bill_patient_name"), facts.get("discharge_patient_name")) in {"variant", "different"}
    checklist = build_checklist(_document_rows(claim), chunks, claim.claim_type_detail, financials["duplicate_bills"], name_review)
    deterministic = build_deterministic_findings(facts, chunks, financials, claim.language)
    questions = follow_up_questions(facts, financials, inconsistencies, checklist, claim.language)
    findings = deterministic
    engine = "demo" if claim.demo_mode else "deterministic"
    live = False
    note = (
        "Demo mode used fictional documents and on-device rules. Sarvam was not called."
        if claim.demo_mode
        else "SARVAM_API_KEY is not configured. Findings quote the uploaded policy text and use deterministic checks. Sarvam-105B was not called."
    )
    overall = "needs_review"
    summary = summary_text(findings, financials, claim.language)

    if not claim.demo_mode and client is not None:
        excerpts = retrieve(chunks, " ".join(filter(None, [facts.get("narrative"), facts.get("diagnosis"), facts.get("procedure"), "room rent consumables waiting bank documents"])))
        try:
            parsed = complete_json(client, analysis_messages(claim.language, excerpts, _public_facts(facts), financials, facts.get("narrative") or ""))
            live = True
            model_findings = reconcile(model_to_findings(parsed), chunks, deterministic)
            findings = model_findings
            engine = "sarvam-105b"
            note = "Explanations were drafted by Sarvam-105B from retrieved policy excerpts. Citations were checked against the stored text. This is not an insurer's decision."
            summary = parsed.summary or summary_text(findings, financials, claim.language)
            overall = parsed.overall_status if parsed.overall_status in {"needs_review", "ready_for_user_review"} else "needs_review"
            extra = [question for question in parsed.follow_up_questions if _question_allowed(question, facts)]
            for question in extra:
                if question not in questions:
                    questions.append(question)
        except InvalidModelOutputError as exc:
            live = True
            engine = "deterministic"
            note = exc.message + " On-device findings are shown instead."
        except AppError as exc:
            live = True
            engine = "deterministic"
            note = exc.message + " On-device findings are shown instead."

    if any(item.get("citation_status") == "unverified" or item["category"] in {"uncertain", "missing_information"} for item in findings):
        overall = "needs_review"

    _save_findings(db, claim, findings)
    _save_checklist(db, claim, checklist)
    db.query(AnalysisRun).filter(AnalysisRun.claim_id == claim.id).delete()
    run = AnalysisRun(
        id=str(uuid.uuid4()),
        claim_id=claim.id,
        engine=engine,
        live_api_call=live,
        summary=summary,
        follow_up_questions_json=questions,
        inconsistencies_json=inconsistencies,
        financials_json=financials,
        overall_status=overall,
        note=note,
    )
    db.add(run)
    if claim.status in {"draft", "documents_uploaded", "analysis_complete"}:
        claim.status = "analysis_complete"
    elif claim.status in {"needs_user_review", "ready_for_submission"}:
        claim.status = "needs_user_review"
        draft = latest_draft(claim)
        if draft:
            draft.reviewed_by_user = False
            draft.user_confirmed = False
    claim.updated_at = utcnow()
    db.flush()
    db.expire(claim, ["findings", "checklist_items", "analysis_runs", "chunks"])
    return run


def _question_allowed(question: str, facts: dict) -> bool:
    lowered = question.casefold()
    if facts.get("admission_date") and ("admission date" in lowered or "भर्ती की तारीख" in question):
        return False
    if facts.get("discharge_date") and ("discharge date" in lowered or "छुट्टी की तारीख" in question):
        return False
    return True


def _public_facts(facts: dict) -> dict:
    hidden = {"line_items", "printed_totals", "bill_records", "amount_paid"}
    public = {}
    for key, value in facts.items():
        if key in hidden:
            continue
        if hasattr(value, "quantize"):
            public[key] = str(value)
        else:
            public[key] = value
    public["line_items"] = [
        {
            "description": item.get("description"),
            "quantity": item.get("quantity"),
            "rate": item.get("rate"),
            "amount": item.get("amount"),
        }
        for item in facts.get("line_items") or []
    ]
    return public


def latest_draft(claim: Claim) -> ClaimDraft | None:
    if not claim.drafts:
        return None
    return sorted(claim.drafts, key=lambda item: item.version)[-1]


def build_draft_payload(claim: Claim, run: AnalysisRun | None = None) -> dict:
    facts = gather_facts(claim)
    financials = run.financials_json if run and run.financials_json else _financials_for(facts)
    findings = [
        {
            "category": finding.category,
            "title": finding.title,
            "explanation": finding.explanation,
            "policy_clause": finding.policy_clause,
            "source_page": finding.source_page,
            "citation_status": finding.citation_status,
            "recommended_next_step": finding.recommended_next_step,
        }
        for finding in claim.findings
    ]
    checklist = [
        {"name": item.name, "status": item.status, "source": item.source}
        for item in claim.checklist_items
    ]
    questions = (run.follow_up_questions_json if run else None) or []
    clauses = []
    for finding in claim.findings:
        if finding.citation_status == "verified" and finding.policy_clause:
            clauses.append(
                {
                    "title": finding.title,
                    "clause": finding.policy_clause,
                    "page": finding.source_page,
                    "category": finding.category,
                    "origin": "Exact text extracted from the uploaded policy",
                }
            )
    present = [document.original_filename for document in claim.documents if document.processing_status in {"completed", "partially_completed"}]
    missing = [item.name for item in claim.checklist_items if item.status == "missing"]
    return {
        "warning": DISCLAIMER,
        "fictional": bool(claim.demo_mode),
        "policyholder_name": facts.get("policyholder_name") or "",
        "insurer_name": facts.get("insurer_name") or "",
        "policy_number": facts.get("policy_number") or "",
        "patient_name": facts.get("bill_patient_name") or facts.get("patient_name") or "",
        "patient_name_on_discharge": facts.get("discharge_patient_name") or "",
        "hospital_name": facts.get("hospital_name") or "",
        "incident_narrative": facts.get("narrative") or "",
        "incident_date": facts.get("incident_date") or "",
        "admission_date": facts.get("admission_date") or "",
        "discharge_date": facts.get("discharge_date") or "",
        "diagnosis": facts.get("diagnosis") or "",
        "procedure": facts.get("procedure") or "",
        "treatment": facts.get("treatment") or "",
        "expenses": [
            {
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "rate": item.get("rate"),
                "amount": item.get("amount"),
            }
            for item in facts.get("line_items") or []
        ],
        "amount_claimed": financials.get("amount_claimed") or "",
        "printed_total": financials.get("printed_total") or "",
        "itemized_total": financials.get("itemized_total") or "",
        "currency": "INR",
        "financials": financials,
        "policy_clauses": clauses,
        "supporting_documents": present,
        "missing_documents": missing,
        "unresolved_questions": questions,
        "findings_for_reference": findings,
        "checklist_for_reference": checklist,
        "declarations": [
            "I have checked this draft against my documents.",
            "I understand Claim-It does not decide coverage or guarantee reimbursement.",
            "I will submit this to the insurer myself. Claim-It has not sent it.",
        ],
    }


def generate_draft(db: Session, claim: Claim, regenerate: bool = False, client=None) -> ClaimDraft:
    if claim.demo_mode:
        client = None
    runs = sorted(claim.analysis_runs, key=lambda item: item.created_at or utcnow())
    run = runs[-1] if runs else None
    if run is None:
        run = run_analysis(db, claim, client=client)
    existing = latest_draft(claim)
    if existing and not regenerate:
        return existing
    payload = build_draft_payload(claim, run)
    version = 1 if not existing else existing.version + 1
    if existing and regenerate:
        existing.draft_json = payload
        existing.version = version
        existing.reviewed_by_user = False
        existing.user_confirmed = False
        existing.updated_at = utcnow()
        draft = existing
    else:
        draft = ClaimDraft(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            draft_json=payload,
            version=version,
            reviewed_by_user=False,
            user_confirmed=False,
        )
        db.add(draft)
    claim.status = "needs_user_review"
    claim.updated_at = utcnow()
    return draft


def recalculate_draft(claim: Claim, draft: ClaimDraft) -> ClaimDraft:
    payload = dict(draft.draft_json or {})
    facts = gather_facts(claim)
    items = payload.get("expenses") or facts["line_items"]
    printed = payload.get("printed_total")
    printed_values = [D(printed)] if D(printed) is not None else facts["printed_totals"]
    financials = build_financials(
        items=items,
        printed_totals=[value for value in printed_values if value is not None],
        amount_paid=facts["amount_paid"],
        amount_claimed=D(payload.get("amount_claimed")),
        room_limit_text=facts.get("room_rent_limit"),
        deductible_text=facts.get("deductible"),
        copay_text=facts.get("copayment"),
        duplicates=duplicate_bill_numbers(facts["bill_records"]),
    )
    payload["financials"] = financials
    payload["itemized_total"] = financials.get("itemized_total") or ""
    payload["printed_total"] = financials.get("printed_total") or payload.get("printed_total") or ""
    payload["amount_claimed"] = payload.get("amount_claimed") or financials.get("amount_claimed") or ""
    payload["warning"] = DISCLAIMER
    draft.draft_json = payload
    draft.version += 1
    draft.updated_at = utcnow()
    claim.updated_at = utcnow()
    return draft


def answer(claim: Claim, question: str, client=None) -> dict:
    question = (question or "").strip()
    if not question:
        raise AppError(400, "empty_question", "Type a question first.")
    chunks = _load_chunks(claim)
    if claim.demo_mode:
        client = None
    if not chunks:
        return {
            "answer": "No policy text is available, so no coverage conclusion was established.",
            "citations": [],
            "engine": "demo" if claim.demo_mode else "none",
            "live_api_call": False,
        }
    excerpts = retrieve(chunks, question, limit=4)
    if client is None:
        citations = [
            {"quote": item["text"], "page_number": item["page_number"], "document_id": item["document_id"]}
            for item in excerpts[:3]
        ]
        lines = [
            "Sarvam-105B was not called. These are exact excerpts from the uploaded policy, not an insurer's decision."
            if not claim.demo_mode
            else "Demo mode did not call Sarvam. These are exact excerpts from the fictional policy, not an insurer's decision."
        ]
        for citation in citations:
            lines.append(f"Page {citation['page_number']}: {citation['quote']}")
        return {
            "answer": "\n\n".join(lines),
            "citations": citations,
            "engine": "demo" if claim.demo_mode else "retrieved_clauses",
            "live_api_call": False,
        }
    try:
        parsed = answer_question(client, claim.language, question, excerpts)
    except AppError as exc:
        citations = [
            {"quote": item["text"], "page_number": item["page_number"], "document_id": item["document_id"]}
            for item in excerpts[:3]
        ]
        return {
            "answer": exc.message + " Exact excerpts are shown instead.",
            "citations": citations,
            "engine": "retrieved_clauses",
            "live_api_call": True,
        }
    citations = []
    for quote in parsed["quotes"]:
        text = (quote.get("quote") or "").strip()
        page = quote.get("page_number") or None
        if page == 0:
            page = None
        match = bind_citation(
            {"category": "uncertain", "policy_clause": text or None, "page_number": page, "explanation": ""},
            excerpts,
        )
        if match.get("citation_status") == "verified":
            citations.append(
                {
                    "quote": text,
                    "page_number": match["source_page"],
                    "document_id": match["source_document_id"],
                }
            )
    if not citations:
        return {
            "answer": "The model did not cite a stored policy clause, so no policy-backed conclusion was established. " + parsed["answer"],
            "citations": [],
            "engine": "sarvam-105b",
            "live_api_call": True,
        }
    return {"answer": parsed["answer"], "citations": citations, "engine": "sarvam-105b", "live_api_call": True}
