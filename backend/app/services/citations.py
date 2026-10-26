"""Reject policy quotes that are not substrings of a stored chunk on the stated page."""

from app.services.textutil import normalize_match


def find_chunk(clause: str | None, page_number: int | None, chunks: list[dict]) -> dict | None:
    if not clause:
        return None
    needle = normalize_match(clause)
    if len(needle) < 24:
        return None
    matches = [chunk for chunk in chunks if needle in normalize_match(chunk.get("text") or "")]
    if not matches:
        return None
    if page_number is not None:
        on_page = [chunk for chunk in matches if int(chunk["page_number"]) == int(page_number)]
        if not on_page:
            return None
        return on_page[0]
    return matches[0]


def bind_citation(finding: dict, chunks: list[dict]) -> dict:
    """Return a copy. Unsupported or excluded findings without a real clause are not policy-backed."""
    result = dict(finding)
    clause = result.get("policy_clause") or None
    page = result.get("source_page")
    if page is None:
        page = result.get("page_number")
    match = find_chunk(clause, page if isinstance(page, int) else None, chunks)
    if clause and match is None:
        if result.get("category") in {"potentially_supported", "potentially_excluded"}:
            result["category"] = "uncertain"
        result["citation_status"] = "unverified"
        result["policy_clause"] = None
        result["source_page"] = None
        result["source_document_id"] = None
        prefix = "The cited policy wording is not in the uploaded document, so this is not a policy-backed conclusion. "
        if not str(result.get("explanation") or "").startswith(prefix):
            result["explanation"] = prefix + str(result.get("explanation") or "")
        return result
    if match:
        result["citation_status"] = "verified"
        result["source_page"] = int(match["page_number"])
        result["source_document_id"] = match["document_id"]
        result["policy_source"] = result.get("policy_source") or "Uploaded policy"
        return result
    if result.get("category") in {"potentially_supported", "potentially_excluded"}:
        result["category"] = "uncertain"
        result["citation_status"] = "unverified"
        result["policy_clause"] = None
        prefix = "No policy clause was cited, so this is not a policy-backed conclusion. "
        if not str(result.get("explanation") or "").startswith(prefix):
            result["explanation"] = prefix + str(result.get("explanation") or "")
        return result
    result["citation_status"] = "none"
    result["policy_clause"] = None
    return result
