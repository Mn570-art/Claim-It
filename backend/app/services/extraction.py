"""Structured field extraction from page text. Missing values stay 'Not found'."""

import re
from decimal import Decimal, InvalidOperation

from app.services.textutil import is_missing_token, normalize_ws, stringify

POLICY_SPECS = [
    ("insurer_name", "Insurer name", r"Insurer name:\s*(.+)"),
    ("policy_number", "Policy number", r"Policy number:\s*([A-Za-z0-9-]+)"),
    ("policyholder_name", "Policyholder name", r"Policyholder name:\s*(.+)"),
    ("policy_type", "Policy type", r"Policy type:\s*(.+)"),
    ("coverage_start", "Coverage start", r"Coverage start:\s*(\d{4}-\d{2}-\d{2})"),
    ("coverage_end", "Coverage end", r"Coverage end:\s*(\d{4}-\d{2}-\d{2})"),
    ("sum_insured", "Sum insured", r"Sum insured:\s*([0-9,]+)"),
    ("deductible", "Deductible", r"Deductible:\s*(.+)"),
    ("copayment", "Co-payment", r"Co-payment:\s*(.+)"),
    ("room_rent_limit", "Room rent limit", r"Room rent limit:\s*(.+)"),
    ("waiting_periods", "Waiting periods", r"Waiting periods:\s*(.+)"),
    ("pre_hospitalization", "Pre-hospitalisation", r"Pre-hospitalisation:\s*(.+)"),
    ("post_hospitalization", "Post-hospitalisation", r"Post-hospitalisation:\s*(.+)"),
    ("required_documents", "Required documents", r"Required documents:\s*(.+)"),
    ("exclusions", "Exclusions", r"Exclusions:\s*(.+)"),
    ("claim_procedure", "Claim procedure", r"Claim procedure:\s*(.+)"),
]

HOSPITAL_SPECS = [
    ("patient_name", "Patient name", r"Patient name:\s*(.+)"),
    ("hospital_name", "Hospital name", r"Hospital name:\s*(.+)"),
    ("admission_date", "Admission date", r"Admission date:\s*(\d{4}-\d{2}-\d{2})"),
    ("discharge_date", "Discharge date", r"Discharge date:\s*(\d{4}-\d{2}-\d{2})"),
    ("diagnosis", "Diagnosis", r"Diagnosis:\s*(.+)"),
    ("procedure", "Procedure", r"Procedure:\s*(.+)"),
    ("treatment", "Treatment", r"Treatment:\s*(.+)"),
    ("bill_number", "Bill number", r"Bill number:\s*([A-Za-z0-9-]+)"),
    ("bill_date", "Bill date", r"Bill date:\s*(\d{4}-\d{2}-\d{2})"),
    ("printed_total", "Printed total", r"Printed total:\s*([0-9,]+\.\d{2}|[0-9,]+)"),
    ("amount_paid", "Amount paid", r"Amount paid:\s*([0-9,]+\.\d{2}|[0-9,]+)"),
    ("bill_status", "Bill status", r"Bill status:\s*(.+)"),
    ("description", "Description", r"Description:\s*(.+)"),
    ("amount", "Amount", r"^Amount:\s*([0-9,]+\.\d{2}|[0-9,]+)"),
]

LINE_RE = re.compile(
    r"^(?P<description>.+?) \| qty (?P<quantity>[0-9.]+) \| rate (?P<rate>[0-9.]+) \| amount (?P<amount>[0-9.]+)\s*$",
    re.IGNORECASE,
)

SPECS_BY_TYPE = {
    "policy": POLICY_SPECS,
    "discharge_summary": [item for item in HOSPITAL_SPECS if item[0] not in {"printed_total", "amount_paid", "bill_number", "bill_date", "bill_status", "description", "amount"}],
    "bill": HOSPITAL_SPECS,
    "prescription": HOSPITAL_SPECS,
    "diagnostic": HOSPITAL_SPECS,
    "claim_form": POLICY_SPECS + HOSPITAL_SPECS,
    "bank_proof": [("policyholder_name", "Account name", r"Account name:\s*(.+)")],
    "other": HOSPITAL_SPECS + POLICY_SPECS,
}


def _field(key: str, label: str, value: str | None, page: int | None, document_id: str, filename: str, status: str) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display": value if value else "Not found",
        "source_document_id": document_id,
        "source_filename": filename,
        "page_number": page if value else None,
        "confidence": "not_available",
        "verification_status": status if value else "not_found",
    }


def _search(pages: list[dict], pattern: str) -> tuple[str | None, int | None, int]:
    regex = re.compile(pattern, re.IGNORECASE)
    hits: list[tuple[str, int]] = []
    for page in pages:
        for line in (page.get("text") or "").splitlines():
            match = regex.search(line.strip())
            if match:
                hits.append((normalize_ws(match.group(1)), int(page["page_number"])))
    if not hits:
        return None, None, 0
    return hits[0][0], hits[0][1], len({page for _, page in hits})


def parse_line_items(pages: list[dict], document_id: str) -> list[dict]:
    items = []
    for page in pages:
        for line in (page.get("text") or "").splitlines():
            match = LINE_RE.match(line.strip())
            if not match:
                continue
            try:
                amount = str(Decimal(match.group("amount")).quantize(Decimal("0.01")))
                rate = str(Decimal(match.group("rate")).quantize(Decimal("0.01")))
                quantity = str(Decimal(match.group("quantity")))
            except InvalidOperation:
                continue
            items.append(
                {
                    "description": normalize_ws(match.group("description")),
                    "quantity": quantity,
                    "rate": rate,
                    "amount": amount,
                    "page_number": int(page["page_number"]),
                    "source_document_id": document_id,
                }
            )
    return items


def extract_fields(pages: list[dict], document_type: str, document_id: str, filename: str) -> dict:
    specs = SPECS_BY_TYPE.get(document_type, SPECS_BY_TYPE["other"])
    seen: set[str] = set()
    fields = []
    for key, label, pattern in specs:
        if key in seen:
            continue
        seen.add(key)
        value, page, page_hits = _search(pages, pattern)
        if value and is_missing_token(value):
            value, page = None, None
        status = "extracted"
        if value and page_hits > 1:
            status = "needs_review"
        fields.append(_field(key, label, value, page, document_id, filename, status))

    line_items = parse_line_items(pages, document_id) if document_type in {"bill", "other", "prescription"} else []
    if document_type == "bill" and not any(field["key"] == "line_items" for field in fields):
        fields.append(
            {
                "key": "line_items",
                "label": "Itemised expenses",
                "value": line_items,
                "display": f"{len(line_items)} items" if line_items else "Not found",
                "source_document_id": document_id,
                "source_filename": filename,
                "page_number": line_items[0]["page_number"] if line_items else None,
                "confidence": "not_available",
                "verification_status": "extracted" if line_items else "not_found",
            }
        )
    return {"fields": fields, "line_items": line_items}


def field_map(payload: dict | None) -> dict[str, dict]:
    if not payload:
        return {}
    fields = payload.get("fields") if isinstance(payload, dict) else None
    if not isinstance(fields, list):
        return {}
    return {item.get("key"): item for item in fields if isinstance(item, dict) and item.get("key")}


def field_value(payload: dict | None, key: str) -> str | None:
    item = field_map(payload).get(key)
    if not item:
        return None
    value = item.get("value")
    if isinstance(value, list):
        return None
    return stringify(value)


def locate_value(pages: list[dict], value: str | None) -> int | None:
    if not value:
        return None
    needle = normalize_ws(value).casefold()
    if len(needle) < 2:
        return None
    found = []
    for page in pages:
        if needle in normalize_ws(page.get("text") or "").casefold():
            found.append(int(page["page_number"]))
    if len(found) == 1:
        return found[0]
    return None


def apply_external_values(
    pages: list[dict],
    document_type: str,
    document_id: str,
    filename: str,
    values: dict,
    annotations: dict | None = None,
) -> dict:
    """Merge Sarvam Extract values into the same field envelope. Nothing is invented."""
    base = extract_fields(pages, document_type, document_id, filename)
    annotations = annotations or {}
    by_key = {field["key"]: field for field in base["fields"]}
    for key, raw in values.items():
        if key not in by_key:
            continue
        value = stringify(raw)
        page = _annotation_page(annotations.get(key)) or locate_value(pages, value)
        confidence = _annotation_confidence(annotations.get(key))
        if value is None:
            by_key[key]["value"] = None
            by_key[key]["display"] = "Not found"
            by_key[key]["page_number"] = None
            by_key[key]["verification_status"] = "not_found"
            by_key[key]["confidence"] = confidence or "not_available"
            continue
        by_key[key]["value"] = value
        by_key[key]["display"] = value
        by_key[key]["page_number"] = page
        by_key[key]["confidence"] = confidence or "not_available"
        by_key[key]["verification_status"] = "needs_review" if page is None else "extracted"
    return {"fields": list(by_key.values()), "line_items": base["line_items"]}


def _annotation_page(node: object) -> int | None:
    if not isinstance(node, dict):
        return None
    sources = node.get("sources") or node.get("source") or []
    if isinstance(sources, dict):
        sources = [sources]
    pages = []
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key in ("page_number", "page", "page_num"):
                if isinstance(source.get(key), int):
                    pages.append(source[key])
                    break
    if len(set(pages)) == 1:
        return pages[0]
    return None


def _annotation_confidence(node: object) -> str | None:
    if not isinstance(node, dict) or "confidence" not in node:
        return None
    try:
        score = float(node["confidence"])
    except (TypeError, ValueError):
        return "not_available"
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"
