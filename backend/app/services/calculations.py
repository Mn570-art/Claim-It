"""Deterministic currency maths. Estimates are never described as payable."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def D(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES)
    text = str(value).strip().replace(",", "").replace("INR", "").replace("₹", "")
    if text == "":
        return None
    try:
        return Decimal(text).quantize(TWOPLACES)
    except (InvalidOperation, ValueError):
        return None


def sum_amounts(amounts: list[Decimal]) -> Decimal:
    total = sum(amounts, ZERO)
    return total.quantize(TWOPLACES)


def money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(TWOPLACES)}"


def difference(printed: Decimal | None, itemized: Decimal) -> Decimal | None:
    if printed is None:
        return None
    return (printed - itemized).quantize(TWOPLACES)


def duplicate_bill_numbers(records: list[dict]) -> list[dict]:
    """records: {bill_number, document_id, filename, amount, description}"""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        number = (record.get("bill_number") or "").strip()
        if number:
            grouped[number].append(record)
    duplicates = []
    for number, rows in grouped.items():
        document_ids = {row.get("document_id") for row in rows}
        repeated_lines = len(rows) > 1 and len(document_ids) == 1
        if len(document_ids) > 1 or repeated_lines:
            duplicates.append(
                {
                    "bill_number": number,
                    "document_ids": sorted(str(item) for item in document_ids if item),
                    "occurrences": len(rows),
                    "note": "The same bill number appears more than once. Compare the documents before using either copy.",
                }
            )
    return duplicates


def room_rent_above_limit(per_day: Decimal | None, limit_per_day: Decimal | None, days: Decimal | None) -> Decimal | None:
    if per_day is None or limit_per_day is None or days is None:
        return None
    if per_day <= limit_per_day:
        return ZERO
    return ((per_day - limit_per_day) * days).quantize(TWOPLACES)


def parse_inr_limit(text: str | None) -> Decimal | None:
    if not text:
        return None
    import re

    match = re.search(r"INR\s*([0-9,]+)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"([0-9,]+)", text)
    return D(match.group(1)) if match else None


def build_financials(
    items: list[dict],
    printed_totals: list[Decimal],
    amount_paid: Decimal | None,
    amount_claimed: Decimal | None,
    room_limit_text: str | None,
    deductible_text: str | None,
    copay_text: str | None,
    duplicates: list[dict],
) -> dict:
    amounts = []
    room_rate = None
    room_days = None
    for item in items:
        amount = D(item.get("amount"))
        if amount is None:
            continue
        amounts.append(amount)
        description = (item.get("description") or "").casefold()
        if "room rent" in description:
            room_rate = D(item.get("rate"))
            room_days = D(item.get("quantity"))
    itemized = sum_amounts(amounts)
    printed = printed_totals[0] if len(printed_totals) == 1 else None
    printed_conflict = len({str(value) for value in printed_totals}) > 1
    gap = difference(printed, itemized) if printed is not None and not printed_conflict else None
    limit = parse_inr_limit(room_limit_text)
    above = room_rent_above_limit(room_rate, limit, room_days)
    deductible = D(deductible_text) if deductible_text is not None and str(deductible_text).strip() in {"0", "0.00", "0.0"} else None
    if deductible_text and deductible is None:
        maybe = D(deductible_text)
        if maybe is not None and "percent" not in deductible_text.casefold() and len(deductible_text) < 12:
            deductible = maybe

    assumptions = [
        "Itemised amounts were added with decimal arithmetic.",
        "The amount claimed is not treated as an approved reimbursement.",
    ]
    unresolved = []
    if gap is not None and gap != ZERO:
        unresolved.append(
            f"The printed total differs from the itemised sum by INR {money(abs(gap))}."
        )
    if printed_conflict:
        unresolved.append("More than one printed total was found. No single printed total was used.")
    if not amounts:
        unresolved.append("No itemised amounts were found, so a documented expense total is not available.")
    if above is not None and above > ZERO:
        unresolved.append(
            "Room rent is above the per-day limit printed in the policy. A proportionate deduction was not calculated, because the policy says it may be applied and does not fix the formula."
        )
    if copay_text:
        assumptions.append(
            "Co-payment was not applied. The schedule limits it to non-network hospitals, and network status was not found."
        )
        unresolved.append("Hospital network status was not found.")
    else:
        unresolved.append("No co-payment term was found, so none was applied.")

    deductible_applied = None
    if deductible is not None:
        deductible_applied = deductible
        assumptions.append(f"The schedule states a deductible of INR {money(deductible)}. It is shown separately and is not a payment promise.")
    else:
        unresolved.append("A deductible amount was not established, so none was applied.")

    estimate_status = "unavailable"
    estimated = None
    # An illustrative figure is only produced when every variable that would change it is known
    # and there is no open sub-limit, discrepancy, or conditional co-pay.
    copay_blocks = bool(copay_text)
    room_blocks = above is not None and above > ZERO
    gap_blocks = (gap is not None and gap != ZERO) or printed_conflict or not amounts
    if deductible is not None and not copay_blocks and not room_blocks and not gap_blocks and amount_claimed is not None:
        estimate_status = "illustrative"
        estimated = (amount_claimed - deductible).quantize(TWOPLACES)
        if estimated < ZERO:
            estimated = ZERO
        assumptions.append("Illustrative figure only: claimed amount minus the stated deductible. This is not payable and not a settlement.")

    if amount_claimed is None and amounts:
        amount_claimed = itemized
        assumptions.append("Amount claimed defaults to the itemised sum, not the printed total, until you edit it.")

    return {
        "currency": "INR",
        "itemized_total": money(itemized),
        "printed_total": money(printed) if not printed_conflict else None,
        "printed_totals_found": [money(value) for value in printed_totals],
        "difference": money(gap) if gap is not None else None,
        "amount_paid_documented": money(amount_paid),
        "amount_claimed": money(amount_claimed),
        "documented_expense_total": money(itemized) if amounts else None,
        "room_rent_per_day": money(room_rate),
        "room_rent_days": money(room_days) if room_days is not None else None,
        "room_rent_limit_per_day": money(limit),
        "room_rent_above_limit": money(above),
        "deductible_applied": money(deductible_applied),
        "copay_applied": None,
        "estimated_reimbursement": money(estimated),
        "estimate_status": estimate_status,
        "estimate_label": "Unavailable" if estimate_status == "unavailable" else "Illustrative only — not payable",
        "assumptions": assumptions,
        "unresolved": unresolved,
        "duplicate_bills": duplicates,
        "line_count": len(amounts),
    }
