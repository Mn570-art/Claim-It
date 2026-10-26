"""Fictional health-claim scenario. Every clause below is copied verbatim into the sample PDFs."""

CLAUSE_21 = (
    "Clause 2.1 Family floater. This policy covers the policyholder and the dependent parents named in the schedule."
)
CLAUSE_41 = (
    "Clause 4.1 Hospitalisation benefit. The Company shall cover medically necessary in-patient treatment in a hospital "
    "in India where the insured person is admitted for more than 24 consecutive hours, up to the sum insured, subject to "
    "the terms, exclusions, and sub-limits of this policy."
)
CLAUSE_42 = (
    "Clause 4.2 Pre and post hospitalisation. Medical expenses incurred for 30 days before admission and 60 days after "
    "discharge are covered when they relate to the same illness, subject to the sum insured."
)
CLAUSE_43 = (
    "Clause 4.3 Room rent sub-limit. Room rent for a non-ICU room is limited to INR 5000 per day. If the insured person "
    "opts for a higher room category, a proportionate deduction may be applied to associated hospital charges. This "
    "sub-limit is not a promise of payment."
)
CLAUSE_46 = (
    "Clause 4.6 Co-payment. A co-payment of 10 percent applies only when treatment is taken at a hospital that is not in "
    "the Company's network. No deductible applies under this schedule."
)
CLAUSE_51 = (
    "Clause 5.1 Waiting periods. A waiting period of 36 months applies to the pre-existing conditions listed in Annexure B, "
    "including hernia, cataract, joint replacement, and kidney stones. Acute conditions that are not listed are not "
    "automatically excluded, and the Company may ask for prior treatment records."
)
CLAUSE_52 = (
    "Clause 5.2 Non-medical consumables. Items such as gloves, toiletries, and other non-medical consumables are excluded "
    "unless the hospital bill shows they were part of a documented surgical package. Where the bill description is "
    "ambiguous, the Company will interpret the item."
)
CLAUSE_71 = (
    "Clause 7.1 Documents for reimbursement. A reimbursement claim must include the policy schedule, discharge summary, "
    "itemised hospital bill, and the signed claim form."
)
CLAUSE_72 = (
    "Clause 7.2 Bank proof. Reimbursement claims require a cancelled cheque or a bank statement in the policyholder's "
    "name before payment can be processed."
)

INSURER = "Narmada Health Assurance"
POLICY_NUMBER = "NHA-HL-2025-88421"
POLICYHOLDER = "Ananya Sharma"
PATIENT_BILL = "Harish Sharma"
PATIENT_DISCHARGE = "Harish K. Sharma"
HOSPITAL = "City Care Hospital, Pune"
POLICY_TYPE = "Family floater health insurance"
COVERAGE_START = "2025-04-01"
COVERAGE_END = "2027-03-31"
SUM_INSURED = "500000"
ADMISSION = "2026-10-12"
DISCHARGE = "2026-10-15"
BILL_NUMBER = "CCH-INV-2026-4419"
DIAGNOSIS = "Acute appendicitis"
PROCEDURE = "Laparoscopic appendectomy"
PRINTED_TOTAL = "99500.00"
AMOUNT_PAID = "99500.00"

LINE_ITEMS = [
    ("Room rent (Single AC, non-ICU)", "3", "8000.00", "24000.00"),
    ("Surgeon fee — appendectomy", "1", "45000.00", "45000.00"),
    ("Anaesthesia", "1", "12000.00", "12000.00"),
    ("Medicines", "1", "8450.00", "8450.00"),
    ("Diagnostics", "1", "6200.00", "6200.00"),
    ("Surgical consumables", "1", "3100.00", "3100.00"),
]

NARRATIVE_EN = (
    "My father Harish Sharma was admitted to City Care Hospital, Pune on 12 October 2026 because of severe abdominal pain. "
    "He stayed for three days, had an appendectomy, and was discharged on 15 October 2026. I have uploaded the policy, "
    "the discharge summary, and the hospital bill. This is a reimbursement claim."
)
NARRATIVE_HI = (
    "मेरे पिता हरीश शर्मा को 12 अक्टूबर 2026 को तेज पेट दर्द की वजह से सिटी केयर अस्पताल, पुणे में भर्ती किया गया। "
    "तीन दिन बाद 15 अक्टूबर को अपेंडेक्टॉमी के बाद उन्हें छुट्टी मिली। मैंने पॉलिसी, डिस्चार्ज समरी और अस्पताल का बिल "
    "अपलोड किया है। यह रीइम्बर्समेंट क्लेम है।"
)

FICTIONAL_BANNER = "FICTIONAL SAMPLE — NOT A REAL INSURER, HOSPITAL, OR PATIENT"
