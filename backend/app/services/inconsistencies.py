"""Deterministic checks. A mismatch is only a prompt to review the documents."""

import re
from datetime import date, datetime

from app.services.calculations import D, ZERO


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    }
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if match and match.group(2).casefold() in months:
        return date(int(match.group(3)), months[match.group(2).casefold()], int(match.group(1)))
    return None


def name_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.casefold() for part in re.findall(r"[A-Za-z]+", value)]


def compare_names(left: str | None, right: str | None) -> str:
    a, b = name_tokens(left), name_tokens(right)
    if not a or not b:
        return "missing"
    if a == b:
        return "same"
    if set(a) <= set(b) or set(b) <= set(a):
        return "variant"
    return "different"


def policy_period_status(start: str | None, end: str | None, incident: str | None) -> str:
    start_d, end_d, incident_d = parse_date(start), parse_date(end), parse_date(incident)
    if not incident_d or not start_d or not end_d:
        return "unknown"
    if start_d <= incident_d <= end_d:
        return "inside"
    if incident_d < start_d:
        return "before"
    return "after"


def build_inconsistencies(facts: dict, financials: dict) -> list[dict]:
    items: list[dict] = []
    bill_name = facts.get("bill_patient_name")
    discharge_name = facts.get("discharge_patient_name")
    relation = compare_names(bill_name, discharge_name)
    if relation == "variant":
        items.append(
            {
                "type": "patient_name_variant",
                "severity": "needs_review",
                "detail": (
                    f"The bill names the patient as '{bill_name}' and the discharge summary names "
                    f"'{discharge_name}'. Confirm they are the same person before the draft is used."
                ),
            }
        )
    elif relation == "different":
        items.append(
            {
                "type": "patient_name_conflict",
                "severity": "needs_review",
                "detail": (
                    f"The bill names '{bill_name}' and the discharge summary names '{discharge_name}'. "
                    "These do not look like the same name. Confirm which document the draft should follow."
                ),
            }
        )

    admission = parse_date(facts.get("admission_date"))
    discharge = parse_date(facts.get("discharge_date"))
    incident = parse_date(facts.get("incident_date"))
    if admission and discharge and discharge < admission:
        items.append(
            {
                "type": "date_order",
                "severity": "needs_review",
                "detail": "The discharge date is earlier than the admission date. Check both documents.",
            }
        )
    if admission and incident and admission != incident:
        items.append(
            {
                "type": "incident_date_conflict",
                "severity": "needs_review",
                "detail": "The incident date on the claim does not match the admission date in the documents.",
            }
        )

    period = policy_period_status(facts.get("coverage_start"), facts.get("coverage_end"), facts.get("incident_date") or facts.get("admission_date"))
    if period in {"before", "after"}:
        items.append(
            {
                "type": "policy_period",
                "severity": "needs_review",
                "detail": "The admission or incident date falls outside the coverage period printed on the policy. This is not a decision that the claim will be rejected.",
            }
        )
    if facts.get("policy_uploaded") and not facts.get("policy_number"):
        items.append(
            {
                "type": "missing_policy_number",
                "severity": "needs_review",
                "detail": "A policy document was uploaded, but no policy number was found in it.",
            }
        )

    gap = D(financials.get("difference"))
    if gap is not None and gap != ZERO:
        items.append(
            {
                "type": "amount_mismatch",
                "severity": "needs_review",
                "detail": (
                    f"The itemised lines total INR {financials.get('itemized_total')} and the printed total is "
                    f"INR {financials.get('printed_total')}. The difference is INR {financials.get('difference')}. "
                    "Check both figures before choosing an amount to claim."
                ),
            }
        )
    for duplicate in financials.get("duplicate_bills") or []:
        items.append(
            {
                "type": "duplicate_bill",
                "severity": "needs_review",
                "detail": (
                    f"Bill number {duplicate.get('bill_number')} appears {duplicate.get('occurrences')} times. "
                    "Compare the copies before using either amount."
                ),
            }
        )
    return items
