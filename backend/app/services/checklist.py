"""Document checklist. Policy requirements are separate from general suggestions."""

from app.services.textutil import normalize_match


def _has_marker(chunks: list[dict], marker: str) -> bool:
    needle = marker.casefold()
    return any(needle in (chunk.get("text") or "").casefold() for chunk in chunks)


def _docs_of_type(documents: list[dict], document_type: str) -> list[dict]:
    return [doc for doc in documents if doc.get("document_type") == document_type]


def _status_for(docs: list[dict]) -> tuple[str, str | None]:
    if not docs:
        return "missing", None
    completed = [doc for doc in docs if doc.get("processing_status") in {"completed", "partially_completed"}]
    if completed:
        return "present", completed[0]["id"]
    failed = [doc for doc in docs if doc.get("processing_status") in {"failed", "rejected"}]
    if failed:
        return "needs_review", failed[0]["id"]
    return "needs_review", docs[0]["id"]


def build_checklist(
    documents: list[dict],
    chunks: list[dict],
    claim_type_detail: str | None,
    duplicates: list[dict],
    name_needs_review: bool,
) -> list[dict]:
    reimbursement_clause = _has_marker(chunks, "clause 7.1")
    bank_clause = _has_marker(chunks, "clause 7.2")
    cashless = claim_type_detail == "cashless"
    items = []

    def add(name: str, reason: str, status: str, source: str, reference: str | None, document_id: str | None) -> None:
        items.append(
            {
                "name": name,
                "reason": reason,
                "status": status,
                "source": source,
                "source_reference": reference,
                "document_id": document_id,
            }
        )

    policy_docs = _docs_of_type(documents, "policy")
    status, doc_id = _status_for(policy_docs)
    if reimbursement_clause:
        add(
            "Policy schedule",
            "Clause 7.1 says a reimbursement claim must include the policy schedule.",
            status,
            "policy_requirement",
            "Clause 7.1",
            doc_id,
        )
    else:
        add(
            "Policy schedule",
            "A policy file is needed before any clause can be quoted. No requirement clause was found in an uploaded policy.",
            status,
            "general_suggestion",
            None,
            doc_id,
        )

    discharge_status, discharge_id = _status_for(_docs_of_type(documents, "discharge_summary"))
    source = "policy_requirement" if reimbursement_clause else "general_suggestion"
    add(
        "Discharge summary",
        "Clause 7.1 lists the discharge summary." if reimbursement_clause else "Hospitals usually issue a discharge summary. The uploaded policy does not currently confirm this.",
        discharge_status,
        source,
        "Clause 7.1" if reimbursement_clause else None,
        discharge_id,
    )

    bill_status, bill_id = _status_for(_docs_of_type(documents, "bill"))
    add(
        "Itemised hospital bill",
        "Clause 7.1 lists the itemised hospital bill." if reimbursement_clause else "An itemised bill is needed to add up expenses. The uploaded policy does not currently confirm this.",
        bill_status,
        source,
        "Clause 7.1" if reimbursement_clause else None,
        bill_id,
    )

    form_status, form_id = _status_for(_docs_of_type(documents, "claim_form"))
    if cashless and reimbursement_clause:
        add(
            "Signed claim form",
            "Clause 7.1 applies to reimbursement claims. This claim is marked cashless, so the form is not applied here.",
            "not_applicable",
            "policy_requirement",
            "Clause 7.1",
            form_id,
        )
    else:
        add(
            "Signed claim form",
            "Clause 7.1 lists the signed claim form." if reimbursement_clause else "Insurers often ask for their own claim form. No such clause was found in the uploaded policy.",
            form_status,
            source,
            "Clause 7.1" if reimbursement_clause else None,
            form_id,
        )

    bank_status, bank_id = _status_for(_docs_of_type(documents, "bank_proof"))
    if cashless and bank_clause:
        add(
            "Cancelled cheque or bank statement",
            "Clause 7.2 applies to reimbursement payment. This claim is marked cashless.",
            "not_applicable",
            "policy_requirement",
            "Clause 7.2",
            bank_id,
        )
    elif bank_clause:
        add(
            "Cancelled cheque or bank statement",
            "Clause 7.2 says reimbursement claims require a cancelled cheque or a bank statement in the policyholder's name.",
            bank_status,
            "policy_requirement",
            "Clause 7.2",
            bank_id,
        )
    else:
        add(
            "Cancelled cheque or bank statement",
            "A bank proof is a common reimbursement requirement. No such clause was found in the uploaded policy.",
            bank_status,
            "general_suggestion",
            None,
            bank_id,
        )

    rx_status, rx_id = _status_for(_docs_of_type(documents, "prescription"))
    add(
        "Prescription",
        "A prescription can support medicines. This is a general suggestion, not a clause found in the policy.",
        rx_status,
        "general_suggestion",
        None,
        rx_id,
    )
    diag_status, diag_id = _status_for(_docs_of_type(documents, "diagnostic"))
    add(
        "Diagnostic report",
        "A diagnostic report can support the diagnosis. This is a general suggestion, not a clause found in the policy.",
        diag_status,
        "general_suggestion",
        None,
        diag_id,
    )

    if duplicates:
        numbers = ", ".join(sorted({item.get("bill_number") or "" for item in duplicates}))
        add(
            "Repeated bill number",
            f"Bill number {numbers} was found on more than one upload. Compare them before relying on the amount.",
            "needs_review",
            "general_suggestion",
            "Calculation check",
            None,
        )
    if name_needs_review:
        add(
            "Patient name match",
            "The patient name is not identical across the hospital documents. Confirm the spelling before you rely on it.",
            "needs_review",
            "general_suggestion",
            "Name comparison",
            None,
        )
    return items


def missing_names(items: list[dict]) -> list[str]:
    return [item["name"] for item in items if item["status"] == "missing"]


def clause_text(chunks: list[dict], marker: str) -> dict | None:
    needle = normalize_match(marker)
    for chunk in chunks:
        if needle in normalize_match(chunk.get("text") or ""):
            return chunk
    return None
