# Claim-It

Claim-It helps a person prepare a health-insurance claim in Hindi or English. It reads an uploaded policy and hospital papers, keeps every extracted field tied to a source, compares those facts with the policy wording, and produces an editable draft.

It prepares a claim. It does not submit one, decide coverage, or promise reimbursement.

> Claim-It provides AI-assisted document analysis and claim preparation for informational purposes. It does not determine official coverage, guarantee reimbursement, or replace advice from your insurer. Please verify all extracted information and policy interpretations before submitting a claim.

## Run it

From two terminals, after the one-time installs below.

Backend, from `backend/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8741
```

Frontend, from `frontend/`:

```bash
npm install
npm run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123).

The API listens on port **8741**. The Next.js app listens on port **43123**. `frontend/.env.example` sets `NEXT_PUBLIC_API_URL=http://127.0.0.1:8741`.

## Sarvam API key

Live speech, document AI, reasoning, and spoken playback need a key from the [Sarvam dashboard](https://indus.sarvam.ai).

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `SARVAM_API_KEY` to the key. Do not commit `.env`, and do not put the key in the frontend.
3. Restart the API. The header changes from “Demo ready” to “Sarvam key on”.

Models used when a key is present, matching the installed `sarvamai` 0.1.39 SDK:

| Job | Call |
| --- | --- |
| Speech to text | `speech_to_text.transcribe`, model `saaras:v4` |
| Document fields | `doc_ai.extract` with a JSON schema. Sparse or image files also use `doc_ai.digitise`. |
| Claim reasoning | `chat.completions`, model `sarvam-105b`, strict JSON schema |
| Spoken answers | `text_to_speech.convert`, model `bulbul:v4-flash` |

SDK 0.1.39 does not accept `output_format` on `digitise` or a language argument on `extract`. Digitise is called with `en-IN` or `hi-IN`. English policy PDFs that already have a text layer are read locally, then field extraction is sent to Sarvam when a key exists.

Without a key, uploads of text PDFs still extract fields on this machine and are labelled as local text. Images fail with a clear message instead of a fake transcription. Speech and playback return a missing-key error. Demo mode never calls Sarvam, even if a key is set.

## Demo mode

On the landing page, **Open fictional demo** loads an invented health claim:

- Policyholder Ananya Sharma, patient Harish Sharma, insurer Narmada Health Assurance.
- A policy, a discharge summary, an itemised bill, and a duplicate pharmacy receipt.
- One clause-backed finding, one room-rent limitation, one uncertain consumables finding, one missing document, and a ₹750 gap between the itemised lines and the printed total.

Every demo screen says the documents are fictional and that Sarvam was not called. The bill arithmetic and the citation checks still run.

You can also start an empty health claim and choose **Use fictional sample documents** inside the workspace. Motor insurance is shown as a future feature and cannot be created.

## What a walkthrough covers

1. Start a health claim, leaving unknown fields blank.
2. Upload a policy and hospital PDFs or photos, or attach the fictional set.
3. Record or type the incident in Hindi or English, then confirm the transcript.
4. Review extracted fields. Missing values stay “Not found”.
5. Compare the claim with retrieved policy clauses. Findings without a real quote are not shown as policy-backed.
6. Read the checklist and the bill differences. Differences are not labelled as fraud.
7. Edit the draft, recalculate, and download PDF, JSON, or the checklist CSV.
8. Mark the draft reviewed, then ready for external submission. Nothing is sent to an insurer.
9. Reopen the claim from Claims. Its status is still there.

Workflow labels are Draft, Documents uploaded, Analysis complete, Needs your review, and Ready for external submission.

## Checks

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npx tsc --noEmit
```

The tests check the fictional sample against the authored policy text, the ₹750 bill gap, citation pages, and the demo path refusing a live client. That is a fixture check, not a measured production accuracy rate.

## Limits

- No insurer submission, payment, diagnosis, or identity verification.
- 10 MB per file and 20 PDF pages, unless you change `MAX_UPLOAD_MB` and `MAX_PDF_PAGES`.
- Claims older than `RETENTION_DAYS` (30 by default) are removed when the API starts. Settings can delete everything immediately.
- Uploaded files are served only through the API for that document id. They are not public URLs, and document text is not written to logs.
- A proportionate room-rent deduction is not invented. The daily excess is shown, and the reimbursement estimate stays unavailable when the formula is not fixed by the policy text.
