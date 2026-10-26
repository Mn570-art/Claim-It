"""Build the fictional sample PDFs. Text is drawn line by line so page numbers stay stable."""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.sample_corpus import (
    ADMISSION,
    AMOUNT_PAID,
    BILL_NUMBER,
    CLAUSE_21,
    CLAUSE_41,
    CLAUSE_42,
    CLAUSE_43,
    CLAUSE_46,
    CLAUSE_51,
    CLAUSE_52,
    CLAUSE_71,
    CLAUSE_72,
    COVERAGE_END,
    COVERAGE_START,
    DIAGNOSIS,
    DISCHARGE,
    FICTIONAL_BANNER,
    HOSPITAL,
    INSURER,
    LINE_ITEMS,
    PATIENT_BILL,
    PATIENT_DISCHARGE,
    POLICY_NUMBER,
    POLICY_TYPE,
    POLICYHOLDER,
    PRINTED_TOTAL,
    PROCEDURE,
    SUM_INSURED,
)

NOTO = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
NOTO_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
NOTO_HI = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"

SAMPLE_FILES = {
    "policy": "narmada-health-policy-fictional.pdf",
    "discharge": "city-care-discharge-summary-fictional.pdf",
    "bill": "city-care-itemised-bill-fictional.pdf",
    "pharmacy": "pharmacy-receipt-duplicate-fictional.pdf",
}


def _register(name: str, path: str) -> bool:
    if not Path(path).exists():
        return False
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, path))
    return True


def _register_fonts() -> tuple[str, str, str | None]:
    regular = "NotoSans" if _register("NotoSans", NOTO) else "Helvetica"
    bold = "NotoSansBold" if _register("NotoSansBold", NOTO_BOLD) else "Helvetica-Bold"
    hindi = "NotoSansDevanagari" if _register("NotoSansDevanagari", NOTO_HI) else None
    return regular, bold, hindi


def _wrap(text: str, width: int = 92) -> list[str]:
    words = text.split()
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


def _draw_pages(path: Path, pages: list[list[str]], hindi_note: str | None = None) -> None:
    regular, bold, hindi_font = _register_fonts()
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    for index, lines in enumerate(pages, start=1):
        pdf.setFillColorRGB(0.45, 0.22, 0.12)
        pdf.setFont(bold, 8)
        pdf.drawString(48, height - 32, FICTIONAL_BANNER)
        pdf.setFillColorRGB(0.08, 0.14, 0.22)
        y = height - 54
        for line in lines:
            font = bold if line.startswith("# ") else regular
            text = line[2:] if line.startswith("# ") else line
            pdf.setFont(font, 11 if font == bold else 9)
            pdf.drawString(48, y, text)
            y -= 16 if font == bold else 13
        if hindi_note and hindi_font and index == 1:
            pdf.setFont(hindi_font, 9)
            pdf.drawString(48, 48, hindi_note)
        pdf.setFont(regular, 8)
        pdf.setFillColorRGB(0.35, 0.4, 0.45)
        pdf.drawString(48, 28, f"Page {index} of {len(pages)}  ·  Fictional document for the Claim-It demo")
        pdf.showPage()
    pdf.save()


def policy_pages() -> list[list[str]]:
    schedule = [
        "# Narmada Health Assurance",
        "# Policy schedule (fictional)",
        "Insurer name: " + INSURER,
        "Policy number: " + POLICY_NUMBER,
        "Policyholder name: " + POLICYHOLDER,
        "Policy type: " + POLICY_TYPE,
        "Coverage start: " + COVERAGE_START,
        "Coverage end: " + COVERAGE_END,
        "Sum insured: " + SUM_INSURED,
        "Deductible: 0",
        "Co-payment: 10 percent at non-network hospitals only",
        "Covered member: Ananya Sharma (self)",
        "Covered member: Harish Sharma (father)",
        "Room rent limit: INR 5000 per day for a non-ICU room",
        "Waiting periods: 36 months for the pre-existing conditions listed in Annexure B",
        "Pre-hospitalisation: 30 days",
        "Post-hospitalisation: 60 days",
        "Required documents: policy schedule, discharge summary, itemised hospital bill, and the signed claim form",
        "Exclusions: Non-medical consumables are excluded unless the bill shows they were part of a documented surgical package. Listed pre-existing conditions are subject to the waiting period in Clause 5.1.",
        "Claim procedure: Submit the reimbursement documents listed in Clause 7.1. The insurer, not this document, decides the claim.",
        "",
        *_wrap(CLAUSE_21),
    ]
    benefits = ["# Benefits", "", *_wrap(CLAUSE_41), "", *_wrap(CLAUSE_42), "", *_wrap(CLAUSE_43), "", *_wrap(CLAUSE_46)]
    exclusions = ["# Exclusions and waiting periods", "", *_wrap(CLAUSE_51), "", *_wrap(CLAUSE_52)]
    claims = ["# Claim documents", "", *_wrap(CLAUSE_71), "", *_wrap(CLAUSE_72)]
    return [schedule, benefits, exclusions, claims]


def discharge_pages() -> list[list[str]]:
    return [[
        "# Discharge summary (fictional)",
        "Hospital name: " + HOSPITAL,
        "Patient name: " + PATIENT_DISCHARGE,
        "Admission date: " + ADMISSION,
        "Discharge date: " + DISCHARGE,
        "Diagnosis: " + DIAGNOSIS,
        "Procedure: " + PROCEDURE,
        "Treatment: Emergency laparoscopic appendectomy after admission for severe abdominal pain.",
        "Course: The patient remained admitted for three days and was discharged in a stable condition.",
        "This summary does not state whether the illness was diagnosed before this admission.",
    ]]


def bill_pages() -> list[list[str]]:
    lines = [
        "# Itemised hospital bill (fictional)",
        "Hospital name: " + HOSPITAL,
        "Patient name: " + PATIENT_BILL,
        "Bill number: " + BILL_NUMBER,
        "Bill date: " + DISCHARGE,
        "Admission date: " + ADMISSION,
        "Discharge date: " + DISCHARGE,
        "Bill status: Final bill",
        "Line items:",
    ]
    for description, qty, rate, amount in LINE_ITEMS:
        lines.append(f"{description} | qty {qty} | rate {rate} | amount {amount}")
    lines.extend([
        "Printed total: " + PRINTED_TOTAL,
        "Amount paid: " + AMOUNT_PAID,
        "The printed total on this fictional bill does not equal the sum of the lines above.",
    ])
    return [lines]


def pharmacy_pages() -> list[list[str]]:
    return [[
        "# Pharmacy receipt (fictional duplicate)",
        "Hospital name: " + HOSPITAL,
        "Patient name: " + PATIENT_BILL,
        "Bill number: " + BILL_NUMBER,
        "Bill date: " + DISCHARGE,
        "Description: Medicines",
        "Amount: 8450.00",
        "This receipt repeats bill number " + BILL_NUMBER + ", which is already printed on the hospital bill.",
    ]]


def ensure_sample_documents(directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    pages = {
        "policy": policy_pages(),
        "discharge": discharge_pages(),
        "bill": bill_pages(),
        "pharmacy": pharmacy_pages(),
    }
    written: dict[str, Path] = {}
    for key, filename in SAMPLE_FILES.items():
        path = directory / filename
        hindi = "यह काल्पनिक दस्तावेज़ है। यह किसी बीमा कंपनी का निर्णय नहीं है।" if key == "discharge" else None
        _draw_pages(path, pages[key], hindi_note=hindi)
        written[key] = path
    return written
