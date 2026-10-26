"""PDF, JSON, and CSV exports. None of these submit a claim."""

import csv
import io
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.workflow import DISCLAIMER

NOTO = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
NOTO_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"


def _fonts() -> tuple[str, str]:
    regular, bold = "Helvetica", "Helvetica-Bold"
    if Path(NOTO).exists():
        if "ClaimSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ClaimSans", NOTO))
        regular = "ClaimSans"
    if Path(NOTO_BOLD).exists():
        if "ClaimSansBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ClaimSansBold", NOTO_BOLD))
        bold = "ClaimSansBold"
    return regular, bold


def _wrap(text: str, width: int = 95) -> list[str]:
    words = str(text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) > width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def render_pdf(claim: dict, draft: dict) -> bytes:
    regular, bold = _fonts()
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 18 * mm

    def ensure(lines: int = 1) -> None:
        nonlocal y
        if y < 20 * mm + lines * 12:
            pdf.showPage()
            y = height - 18 * mm
            pdf.setFillColorRGB(0.08, 0.13, 0.2)

    def heading(text: str) -> None:
        nonlocal y
        ensure(2)
        pdf.setFont(bold, 12)
        pdf.setFillColorRGB(0.07, 0.18, 0.24)
        pdf.drawString(18 * mm, y, text)
        y -= 16

    def paragraph(text: str, size: int = 9) -> None:
        nonlocal y
        pdf.setFont(regular, size)
        pdf.setFillColorRGB(0.1, 0.14, 0.2)
        for line in _wrap(text):
            ensure()
            pdf.drawString(18 * mm, y, line)
            y -= 12

    pdf.setTitle(f"Claim-It draft {claim.get('claim_reference')}")
    pdf.setFillColorRGB(0.45, 0.2, 0.1)
    pdf.setFont(bold, 8)
    banner = "DRAFT — NOT SUBMITTED TO AN INSURER"
    if draft.get("fictional") or claim.get("demo_mode"):
        banner = "FICTIONAL DEMO  ·  " + banner
    pdf.drawString(18 * mm, y, banner)
    y -= 16
    pdf.setFillColorRGB(0.07, 0.16, 0.28)
    pdf.setFont(bold, 16)
    pdf.drawString(18 * mm, y, "Claim-It claim draft")
    y -= 16
    paragraph(f"Reference {claim.get('claim_reference')}  ·  Status {claim.get('status', '').replace('_', ' ')}", 10)
    paragraph(DISCLAIMER)
    y -= 6

    heading("People and policy")
    for label, key in (
        ("Policyholder", "policyholder_name"),
        ("Insurer", "insurer_name"),
        ("Policy number", "policy_number"),
        ("Patient on the bill", "patient_name"),
        ("Patient on the discharge summary", "patient_name_on_discharge"),
        ("Hospital", "hospital_name"),
        ("Incident date", "incident_date"),
        ("Admission", "admission_date"),
        ("Discharge", "discharge_date"),
        ("Diagnosis as documented", "diagnosis"),
        ("Procedure as documented", "procedure"),
    ):
        value = draft.get(key) or "Not found"
        paragraph(f"{label}: {value}")

    heading("Incident narrative")
    paragraph(draft.get("incident_narrative") or "Not found")

    heading("Expenses")
    paragraph("Amounts below are documented figures. They are not a reimbursement.")
    for expense in draft.get("expenses") or []:
        paragraph(
            f"{expense.get('description')}: qty {expense.get('quantity')} × {expense.get('rate')} = INR {expense.get('amount')}"
        )
    paragraph(f"Itemised total: INR {draft.get('itemized_total') or 'Not found'}")
    paragraph(f"Printed total: INR {draft.get('printed_total') or 'Not found'}")
    paragraph(f"Amount entered on this draft: INR {draft.get('amount_claimed') or 'Not found'}")
    financials = draft.get("financials") or {}
    paragraph(f"Estimate: {financials.get('estimate_label') or 'Unavailable'}")
    for note in financials.get("unresolved") or []:
        paragraph(f"Unresolved: {note}")

    heading("Policy clauses quoted from the upload")
    clauses = draft.get("policy_clauses") or []
    if not clauses:
        paragraph("No verified policy clause was available.")
    for clause in clauses:
        paragraph(f"{clause.get('title')} — page {clause.get('page') or 'not stated'} ({clause.get('origin')})")
        paragraph(clause.get("clause") or "")
        y -= 4

    heading("Documents")
    paragraph("Uploaded: " + (", ".join(draft.get("supporting_documents") or []) or "None"))
    paragraph("Missing: " + (", ".join(draft.get("missing_documents") or []) or "None recorded"))

    heading("Unresolved questions")
    questions = draft.get("unresolved_questions") or []
    if not questions:
        paragraph("None recorded.")
    for question in questions:
        paragraph(f"• {question}")

    heading("Declarations still requiring the user")
    for item in draft.get("declarations") or []:
        paragraph(f"• {item}")
    paragraph("Reviewed by user: " + ("yes" if claim.get("reviewed_by_user") else "no"))
    paragraph("Marked ready for external submission: " + ("yes" if claim.get("ready_for_submission") else "no"))
    paragraph("Claim-It did not send this draft to an insurer.")
    pdf.save()
    return buffer.getvalue()


def render_json(bundle: dict) -> bytes:
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")


def render_checklist_csv(items: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["document_name", "reason", "status", "source", "source_reference"])
    for item in items:
        writer.writerow(
            [
                item.get("name") or "",
                item.get("reason") or "",
                item.get("status") or "",
                item.get("source") or "",
                item.get("source_reference") or "",
            ]
        )
    return buffer.getvalue().encode("utf-8")
