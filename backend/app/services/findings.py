"""Rule-based findings. Every policy-backed finding quotes a stored clause."""

from app.services.calculations import D, ZERO
from app.services.checklist import clause_text
from app.services.sample_corpus import (
    CLAUSE_41,
    CLAUSE_43,
    CLAUSE_51,
    CLAUSE_52,
    CLAUSE_72,
)
from app.services.textutil import normalize_match

def _quote(chunks: list[dict], marker: str, fallback: str) -> dict | None:
    exact = normalize_match(fallback)
    for chunk in chunks:
        if exact in normalize_match(chunk.get("text") or ""):
            return {"clause": fallback, "page": chunk["page_number"], "document_id": chunk["document_id"]}
    chunk = clause_text(chunks, marker)
    if not chunk:
        return None
    return {"clause": chunk["text"], "page": chunk["page_number"], "document_id": chunk["document_id"]}


def _base(**kwargs) -> dict:
    kwargs.setdefault("supporting_evidence", [])
    kwargs.setdefault("missing_information", [])
    kwargs.setdefault("policy_source", "Uploaded policy")
    kwargs.setdefault("review_status", "needs_review")
    return kwargs


def build_deterministic_findings(facts: dict, chunks: list[dict], financials: dict, language: str) -> list[dict]:
    hi = language == "hi"
    findings: list[dict] = []
    if not chunks:
        findings.append(
            _base(
                code="no_policy",
                category="uncertain",
                title="पॉलिसी का पाठ नहीं मिला" if hi else "No policy text was found",
                explanation=(
                    "अपलोड की गई पॉलिसी में कोई खंड नहीं मिला, इसलिए कवरेज का कोई निष्कर्ष नहीं निकाला गया।"
                    if hi
                    else "No policy wording was found in the uploaded files, so no coverage conclusion was established."
                ),
                policy_clause=None,
                policy_source=None,
                source_document_id=None,
                source_page=None,
                citation_status="none",
                recommended_next_step="Upload the policy PDF, then run the analysis again." if not hi else "पॉलिसी PDF अपलोड करके विश्लेषण दोबारा चलाएँ।",
                missing_information=["Insurance policy"],
            )
        )
        return findings

    admission = facts.get("admission_date")
    discharge = facts.get("discharge_date")
    hosp = _quote(chunks, "clause 4.1", CLAUSE_41)
    if hosp and admission and discharge:
        findings.append(
            _base(
                code="hospitalization",
                category="potentially_supported",
                title="भर्ती 24 घंटे की शर्त से मेल खाती है" if hi else "In-patient stay meets the 24-hour wording",
                explanation=(
                    f"दस्तावेज़ों में भर्ती {admission} और छुट्टी {discharge} है। धारा 4.1 चौबीस घंटे से अधिक की इन-पेशेंट भर्ती की बात करती है। यह बीमाकर्ता का निर्णय नहीं है।"
                    if hi
                    else (
                        f"The documents show admission on {admission} and discharge on {discharge}, which is longer than 24 hours. "
                        "Clause 4.1 describes cover for that kind of in-patient stay, subject to the rest of the policy. "
                        "This is not an insurer's decision."
                    )
                ),
                policy_clause=hosp["clause"],
                source_document_id=hosp["document_id"],
                source_page=hosp["page"],
                citation_status="verified",
                supporting_evidence=[
                    f"Admission date: {admission}",
                    f"Discharge date: {discharge}",
                    f"Diagnosis as documented: {facts.get('diagnosis') or 'Not found'}",
                ],
                recommended_next_step="Keep the discharge summary with the claim draft and let the insurer apply the rest of the terms.",
            )
        )
    elif hosp:
        findings.append(
            _base(
                code="hospitalization_missing_dates",
                category="missing_information",
                title="Admission length is not established",
                explanation="Clause 4.1 was found, but both an admission date and a discharge date are needed before that wording can be compared with the stay.",
                policy_clause=hosp["clause"],
                source_document_id=hosp["document_id"],
                source_page=hosp["page"],
                citation_status="verified",
                missing_information=["Admission date", "Discharge date"],
                recommended_next_step="Add the discharge summary or type the admission and discharge dates.",
            )
        )

    room = _quote(chunks, "clause 4.3", CLAUSE_43)
    above = D(financials.get("room_rent_above_limit"))
    per_day = financials.get("room_rent_per_day")
    limit = financials.get("room_rent_limit_per_day")
    if room and above is not None and above > ZERO and per_day and limit:
        findings.append(
            _base(
                code="room_rent",
                category="potentially_excluded",
                title="रूम रेंट सीमा से ऊपर है" if hi else "Room rent is above the non-ICU sub-limit",
                explanation=(
                    f"बिल में नॉन-आईसीयू रूम रेंट INR {per_day} प्रति दिन है। धारा 4.3 सीमा INR {limit} प्रति दिन बताती है और कहती है कि आनुपातिक कटौती लागू हो सकती है। यह अस्वीकृति नहीं है, और देय राशि की गणना नहीं की गई है।"
                    if hi
                    else (
                        f"The bill shows non-ICU room rent of INR {per_day} per day. Clause 4.3 limits that rent to INR {limit} per day "
                        "and says a proportionate deduction may be applied. That is a limitation, not a denial, and no payable amount was calculated."
                    )
                ),
                policy_clause=room["clause"],
                source_document_id=room["document_id"],
                source_page=room["page"],
                citation_status="verified",
                supporting_evidence=[f"Room rent charged per day: INR {per_day}", f"Amount above the stated limit, before any proportionate rule: INR {financials.get('room_rent_above_limit')}"],
                missing_information=["The policy does not fix the proportionate-deduction formula."],
                recommended_next_step="Ask the insurer how Clause 4.3 is applied. Do not treat the difference as a final deduction.",
            )
        )

    consumable = _quote(chunks, "clause 5.2", CLAUSE_52)
    consumable_items = [item for item in facts.get("line_items") or [] if "consum" in (item.get("description") or "").casefold()]
    if consumable and consumable_items:
        descriptions = ", ".join(item["description"] for item in consumable_items)
        findings.append(
            _base(
                code="consumables",
                category="uncertain",
                title="सर्जिकल कंज्यूमेबल की व्याख्या बाकी है" if hi else "Surgical consumables need the insurer's reading",
                explanation=(
                    f"बिल में '{descriptions}' है। धारा 5.2 गैर-चिकित्सा कंज्यूमेबल को बाहर रखती है, जब तक कि वे दस्तावेज़ी सर्जिकल पैकेज का हिस्सा न हों। बिल यह स्पष्ट नहीं करता, इसलिए निष्कर्ष अनिश्चित है।"
                    if hi
                    else (
                        f"The bill includes '{descriptions}'. Clause 5.2 excludes non-medical consumables unless they are part of a documented surgical package. "
                        "The bill line does not say which of those applies, so the result is uncertain."
                    )
                ),
                policy_clause=consumable["clause"],
                source_document_id=consumable["document_id"],
                source_page=consumable["page"],
                citation_status="verified",
                supporting_evidence=[f"{item['description']}: INR {item['amount']}" for item in consumable_items],
                missing_information=["Whether the consumable line is part of a surgical package."],
                recommended_next_step="Ask the hospital for a break-up, or leave the line for the insurer to interpret.",
            )
        )

    waiting = _quote(chunks, "clause 5.1", CLAUSE_51)
    diagnosis = facts.get("diagnosis")
    if waiting and diagnosis:
        findings.append(
            _base(
                code="waiting_period",
                category="uncertain",
                title="वेटिंग पीरियड अपने आप लागू नहीं होता" if hi else "The waiting-period list does not name this diagnosis",
                explanation=(
                    f"दस्तावेज़ में निदान '{diagnosis}' लिखा है। धारा 5.1 हर्निया, मोतियाबिंद, जॉइंट रिप्लेसमेंट और किडनी स्टोन जैसी सूचीबद्ध बीमारियों पर 36 महीने की प्रतीक्षा बताती है। यह निदान उस सूची में नहीं है, पर बीमाकर्ता पुराने रिकॉर्ड माँग सकता है। इसे बाहर नहीं माना गया।"
                    if hi
                    else (
                        f"The document states the diagnosis as '{diagnosis}'. Clause 5.1 applies a 36-month wait to listed conditions "
                        "such as hernia, cataract, joint replacement, and kidney stones. This diagnosis is not in that list. "
                        "It was not treated as an exclusion. The insurer may still ask for earlier records."
                    )
                ),
                policy_clause=waiting["clause"],
                source_document_id=waiting["document_id"],
                source_page=waiting["page"],
                citation_status="verified",
                supporting_evidence=[f"Diagnosis as documented: {diagnosis}"],
                missing_information=["Whether the illness was treated before this admission."],
                recommended_next_step="If you have earlier prescriptions, keep them ready. Do not assume the waiting period applies.",
            )
        )

    bank = _quote(chunks, "clause 7.2", CLAUSE_72)
    if bank and facts.get("claim_type_detail") != "cashless" and not facts.get("has_bank_proof"):
        findings.append(
            _base(
                code="bank_proof",
                category="missing_information",
                title="रीइम्बर्समेंट के लिए बैंक प्रमाण नहीं मिला" if hi else "Bank proof for reimbursement was not found",
                explanation=(
                    "धारा 7.2 रीइम्बर्समेंट से पहले पॉलिसीधारक के नाम का रद्द चेक या बैंक स्टेटमेंट माँगती है। ऐसा दस्तावेज़ अपलोड नहीं है।"
                    if hi
                    else "Clause 7.2 says a reimbursement claim needs a cancelled cheque or a bank statement in the policyholder's name. No such file has been uploaded."
                ),
                policy_clause=bank["clause"],
                source_document_id=bank["document_id"],
                source_page=bank["page"],
                citation_status="verified",
                missing_information=["Cancelled cheque or bank statement"],
                recommended_next_step="Upload a cancelled cheque or bank statement when you have it. The draft can still be reviewed.",
            )
        )

    gap = D(financials.get("difference"))
    if gap is not None and gap != ZERO:
        findings.append(
            _base(
                code="bill_total",
                category="missing_information",
                title="बिल का योग मेल नहीं खाता" if hi else "Printed bill total does not match the itemised lines",
                explanation=(
                    f"मदों का योग INR {financials.get('itemized_total')} है और छपा कुल INR {financials.get('printed_total')} है। अंतर INR {financials.get('difference')} है। राशि चुनने से पहले बिल जाँच लें।"
                    if hi
                    else (
                        f"The lines add up to INR {financials.get('itemized_total')} and the bill prints INR {financials.get('printed_total')}. "
                        f"The difference is INR {financials.get('difference')}. Check the bill before choosing an amount to claim."
                    )
                ),
                policy_clause=None,
                policy_source=None,
                source_document_id=None,
                source_page=None,
                citation_status="none",
                supporting_evidence=[
                    f"Itemised total: INR {financials.get('itemized_total')}",
                    f"Printed total: INR {financials.get('printed_total')}",
                ],
                missing_information=["Which total should be claimed."],
                recommended_next_step="Choose the amount in the draft after you check the bill. Neither figure is a payable amount.",
            )
        )
    return findings


def follow_up_questions(facts: dict, financials: dict, inconsistencies: list[dict], checklist: list[dict], language: str) -> list[str]:
    hi = language == "hi"
    questions: list[str] = []
    known_admission = bool(facts.get("admission_date"))
    known_discharge = bool(facts.get("discharge_date"))
    treatment = (facts.get("treatment") or "") + " " + (facts.get("narrative") or "")
    emergency_known = "emergency" in treatment.casefold() or "इमरजेंसी" in treatment or "आपात" in treatment

    def ask(text: str) -> None:
        if text not in questions:
            questions.append(text)

    for item in inconsistencies:
        if item["type"] in {"patient_name_variant", "patient_name_conflict"}:
            ask(
                "डिस्चार्ज समरी और बिल में मरीज़ का नाम एक जैसा नहीं है। क्या दोनों एक ही व्यक्ति हैं?"
                if hi
                else "The patient name on the discharge summary does not match the bill exactly. Are they the same person?"
            )
    if not known_admission:
        ask("भर्ती की तारीख क्या है?" if hi else "What was the admission date?")
    if not known_discharge:
        ask("छुट्टी की तारीख क्या है?" if hi else "What was the discharge date?")
    if not emergency_known:
        ask("क्या इलाज आपात स्थिति में हुआ था या पहले से तय था?" if hi else "Was the treatment an emergency or planned?")
    if not facts.get("claim_type_detail"):
        ask(
            "क्या खर्च बीमा कंपनी ने सीधे चुकाया था, या मरीज़ ने चुकाया?"
            if hi
            else "Was the bill paid by the insurer, or paid by the patient and now claimed as reimbursement?"
        )
    if D(financials.get("difference")) not in (None, ZERO):
        ask(
            f"मदों का योग INR {financials.get('itemized_total')} है और छपा कुल INR {financials.get('printed_total')} है। ड्राफ्ट में कौन सी राशि रखें?"
            if hi
            else f"The itemised lines total INR {financials.get('itemized_total')} and the bill prints INR {financials.get('printed_total')}. Which amount should the draft use?"
        )
    if not facts.get("bill_status"):
        ask("क्या बिल अंतिम है या अनंतिम?" if hi else "Is the bill final or provisional?")
    missing = {item["name"] for item in checklist if item["status"] == "missing"}
    if "Discharge summary" in missing:
        ask("क्या डिस्चार्ज समरी उपलब्ध है?" if hi else "Is a discharge summary available?")
    if "Signed claim form" in missing:
        ask("क्या बीमा कंपनी का भरा हुआ क्लेम फॉर्म उपलब्ध है?" if hi else "Is the insurer's signed claim form available?")
    if "Cancelled cheque or bank statement" in missing:
        ask("क्या रद्द चेक या बैंक स्टेटमेंट उपलब्ध है?" if hi else "Is a cancelled cheque or bank statement available?")
    if known_admission:
        questions = [question for question in questions if "admission date" not in question.casefold() and "भर्ती की तारीख" not in question]
    return questions[:8]


def summary_text(findings: list[dict], financials: dict, language: str) -> str:
    counts = {key: 0 for key in ("potentially_supported", "potentially_excluded", "uncertain", "missing_information")}
    for finding in findings:
        if finding["category"] in counts and finding.get("citation_status") != "unverified":
            counts[finding["category"]] += 1
    if language == "hi":
        return (
            f"यह तैयारी का सार है, बीमा निर्णय नहीं। संभावित समर्थन {counts['potentially_supported']}, "
            f"संभावित सीमा {counts['potentially_excluded']}, अनिश्चित {counts['uncertain']}, "
            f"छूटी जानकारी {counts['missing_information']}। दस्तावेज़ी खर्च INR {financials.get('documented_expense_total') or 'Not found'}।"
        )
    return (
        f"This is a preparation summary, not an insurer's decision. "
        f"{counts['potentially_supported']} potentially supported, {counts['potentially_excluded']} potentially limited, "
        f"{counts['uncertain']} uncertain, {counts['missing_information']} missing information. "
        f"Documented expenses: INR {financials.get('documented_expense_total') or 'Not found'}."
    )
