from datetime import date
from decimal import Decimal

from app.services.calculations import D, build_financials, difference, duplicate_bill_numbers, sum_amounts
from app.services.inconsistencies import compare_names, parse_date, policy_period_status


def test_decimal_sum_avoids_binary_float_error():
    total = sum_amounts([Decimal("0.10"), Decimal("0.20")])
    assert total == Decimal("0.30")
    assert difference(Decimal("99500.00"), Decimal("98750.00")) == Decimal("750.00")


def test_duplicate_bill_numbers_across_documents():
    duplicates = duplicate_bill_numbers(
        [
            {"bill_number": "CCH-INV-2026-4419", "document_id": "a"},
            {"bill_number": "CCH-INV-2026-4419", "document_id": "b"},
            {"bill_number": "OTHER", "document_id": "c"},
        ]
    )
    assert len(duplicates) == 1
    assert duplicates[0]["bill_number"] == "CCH-INV-2026-4419"
    assert "fraud" not in duplicates[0]["note"].lower()


def test_sample_financials_do_not_invent_a_payable_amount():
    items = [
        {"description": "Room rent (Single AC, non-ICU)", "quantity": "3", "rate": "8000.00", "amount": "24000.00"},
        {"description": "Surgeon fee — appendectomy", "quantity": "1", "rate": "45000.00", "amount": "45000.00"},
        {"description": "Anaesthesia", "quantity": "1", "rate": "12000.00", "amount": "12000.00"},
        {"description": "Medicines", "quantity": "1", "rate": "8450.00", "amount": "8450.00"},
        {"description": "Diagnostics", "quantity": "1", "rate": "6200.00", "amount": "6200.00"},
        {"description": "Surgical consumables", "quantity": "1", "rate": "3100.00", "amount": "3100.00"},
    ]
    summary = build_financials(
        items=items,
        printed_totals=[Decimal("99500.00")],
        amount_paid=Decimal("99500.00"),
        amount_claimed=None,
        room_limit_text="INR 5000 per day for a non-ICU room",
        deductible_text="0",
        copay_text="10 percent at non-network hospitals only",
        duplicates=[{"bill_number": "CCH-INV-2026-4419"}],
    )
    assert summary["itemized_total"] == "98750.00"
    assert summary["printed_total"] == "99500.00"
    assert summary["difference"] == "750.00"
    assert summary["amount_claimed"] == "98750.00"
    assert summary["amount_paid_documented"] == "99500.00"
    assert summary["copay_applied"] is None
    assert summary["estimated_reimbursement"] is None
    assert summary["estimate_status"] == "unavailable"
    assert summary["room_rent_above_limit"] == "9000.00"
    assert "not" in summary["estimate_label"].lower() or summary["estimate_status"] == "unavailable"


def test_dates_and_name_variants():
    assert parse_date("2026-10-12") == date(2026, 10, 12)
    assert parse_date("12 October 2026") == date(2026, 10, 12)
    assert policy_period_status("2025-04-01", "2027-03-31", "2026-10-12") == "inside"
    assert policy_period_status("2025-04-01", "2027-03-31", "2024-01-01") == "before"
    assert policy_period_status("2025-04-01", "2027-03-31", "2028-01-01") == "after"
    assert policy_period_status(None, "2027-03-31", "2026-10-12") == "unknown"
    assert compare_names("Harish Sharma", "Harish K. Sharma") == "variant"
    assert compare_names("Harish Sharma", "Harish Sharma") == "same"
    assert compare_names("Ananya Sharma", "Harish Sharma") == "different"


def test_money_parser_rejects_words():
    assert D("not a number") is None
    assert D("1,250.50") == Decimal("1250.50")
