from app.services.citations import bind_citation
from app.services.extraction import extract_fields
from app.services.files import extract_pdf_pages
from app.services.findings import build_deterministic_findings, follow_up_questions
from app.services.retrieval import chunk_pages, retrieve
from app.services.sample_corpus import CLAUSE_43, CLAUSE_51
from app.services.sample_docs import ensure_sample_documents
from app.services.sarvam_chat import parse_model_payload
from app.core.errors import InvalidModelOutputError
import pytest


def _policy_chunks(tmp_path):
    paths = ensure_sample_documents(tmp_path)
    pages = extract_pdf_pages(paths["policy"].read_bytes())
    return chunk_pages(pages, "claim", "policy-doc"), pages


def test_extraction_marks_missing_fields_and_does_not_invent_them(tmp_path):
    pages = [{"page_number": 1, "text": "Insurer name: Example Cover\nPolicyholder name: Asha Rao\n"}]
    extracted = extract_fields(pages, "policy", "doc", "policy.pdf")
    values = {field["key"]: field for field in extracted["fields"]}
    assert values["insurer_name"]["value"] == "Example Cover"
    assert values["insurer_name"]["page_number"] == 1
    assert values["policy_number"]["value"] is None
    assert values["policy_number"]["display"] == "Not found"
    assert values["policy_number"]["verification_status"] == "not_found"
    assert values["sum_insured"]["value"] is None


def test_sample_policy_retrieval_returns_room_rent_clause(tmp_path):
    chunks, _pages = _policy_chunks(tmp_path)
    found = retrieve(chunks, "room rent sub-limit single AC", limit=4)
    text = " ".join(chunk["text"] for chunk in found)
    assert "Clause 4.3" in text
    room = next(chunk for chunk in chunks if "Clause 4.3" in chunk["text"])
    assert room["page_number"] == 2
    waiting = next(chunk for chunk in chunks if "Acute conditions that are not listed" in chunk["text"])
    assert CLAUSE_51[:40] in waiting["text"] or "36 months applies" in waiting["text"]
    assert waiting["page_number"] == 3


def test_invented_clause_is_not_policy_backed(tmp_path):
    chunks, _pages = _policy_chunks(tmp_path)
    finding = bind_citation(
        {
            "category": "potentially_supported",
            "title": "Invented",
            "explanation": "The model made this up.",
            "policy_clause": "Clause 9.9 The Company shall pay every bill in full.",
            "page_number": 2,
        },
        chunks,
    )
    assert finding["category"] == "uncertain"
    assert finding["citation_status"] == "unverified"
    assert finding["policy_clause"] is None
    assert "not a policy-backed conclusion" in finding["explanation"]


def test_real_clause_keeps_its_page(tmp_path):
    chunks, _pages = _policy_chunks(tmp_path)
    finding = bind_citation(
        {
            "category": "potentially_excluded",
            "title": "Room",
            "explanation": "Limit may apply.",
            "policy_clause": CLAUSE_43,
            "page_number": 2,
        },
        chunks,
    )
    assert finding["citation_status"] == "verified"
    assert finding["source_page"] == 2
    assert finding["category"] == "potentially_excluded"


def test_wrong_page_rejects_an_otherwise_real_quote(tmp_path):
    chunks, _pages = _policy_chunks(tmp_path)
    finding = bind_citation(
        {
            "category": "potentially_supported",
            "explanation": "Quoted the right words on the wrong page.",
            "policy_clause": CLAUSE_43,
            "page_number": 4,
        },
        chunks,
    )
    assert finding["citation_status"] == "unverified"
    assert finding["category"] == "uncertain"


def test_follow_ups_skip_known_admission_date():
    facts = {
        "admission_date": "2026-10-12",
        "discharge_date": "2026-10-15",
        "treatment": "Emergency laparoscopic appendectomy",
        "narrative": "emergency admission",
        "claim_type_detail": "reimbursement",
        "bill_status": "Final bill",
    }
    questions = follow_up_questions(facts, {"difference": "0.00"}, [], [], "en")
    assert all("admission date" not in question.casefold() for question in questions)


def test_invalid_model_json_is_rejected():
    with pytest.raises(InvalidModelOutputError):
        parse_model_payload("not json")
    with pytest.raises(InvalidModelOutputError):
        parse_model_payload('{"summary": "x"}')


def test_sample_fields_match_the_fictional_policy(tmp_path):
    paths = ensure_sample_documents(tmp_path)
    pages = extract_pdf_pages(paths["policy"].read_bytes())
    extracted = extract_fields(pages, "policy", "doc", paths["policy"].name)
    values = {field["key"]: field["value"] for field in extracted["fields"]}
    assert values["policy_number"] == "NHA-HL-2025-88421"
    assert values["policyholder_name"] == "Ananya Sharma"
    assert values["sum_insured"] == "500000"
    assert values["coverage_start"] == "2025-04-01"
    assert values["coverage_end"] == "2027-03-31"
    assert "signed claim form" in values["required_documents"]
    bill_pages = extract_pdf_pages(paths["bill"].read_bytes())
    bill = extract_fields(bill_pages, "bill", "bill", paths["bill"].name)
    assert len(bill["line_items"]) == 6
    assert bill["line_items"][0]["amount"] == "24000.00"
