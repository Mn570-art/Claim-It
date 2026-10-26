import io

from pypdf import PdfReader

from app.services.sample_docs import ensure_sample_documents


def test_health_and_settings(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["sarvam_configured"] is False
    settings = client.patch("/api/settings", json={"preferred_language": "hi", "voice_playback": False})
    assert settings.status_code == 200
    assert settings.json()["preferred_language"] == "hi"
    assert settings.json()["voice_playback"] is False


def test_demo_claim_end_to_end(client, tmp_path):
    created = client.post("/api/demo/seed?language=en&stage=ready")
    assert created.status_code == 200
    claim = created.json()
    assert claim["demo_mode"] is True
    assert claim["status"] == "needs_user_review"
    assert claim["analysis"]["engine"] == "demo"
    assert claim["analysis"]["live_api_call"] is False
    assert all(document["live_api_call"] is False for document in claim["documents"])
    assert claim["analysis"]["financials"]["difference"] == "750.00"
    assert claim["analysis"]["financials"]["estimated_reimbursement"] is None
    categories = {finding["category"] for finding in claim["findings"]}
    assert categories == {"potentially_supported", "potentially_excluded", "uncertain", "missing_information"}
    supported = next(item for item in claim["findings"] if item["category"] == "potentially_supported")
    assert supported["citation_status"] == "verified"
    assert supported["source_page"] == 2
    assert "Clause 4.1" in supported["policy_clause"]
    waiting = next(item for item in claim["findings"] if "waiting" in item["title"].lower())
    assert waiting["source_page"] == 3
    assert any(item["status"] == "missing" and item["source"] == "policy_requirement" for item in claim["checklist"])
    assert any(item["type"] == "duplicate_bill" for item in claim["analysis"]["inconsistencies"])
    assert all("admission date" not in question.lower() for question in claim["analysis"]["follow_up_questions"])

    edited = client.patch(
        f"/api/claims/{claim['id']}/draft",
        json={"incident_narrative": "Edited fictional narrative for the demo.", "amount_claimed": "90000.00"},
    )
    assert edited.status_code == 200
    assert edited.json()["version"] == 2
    assert edited.json()["draft"]["amount_claimed"] == "90000.00"
    assert "not sent" in edited.json()["draft"]["declarations"][-1].lower() or "not sent" in " ".join(edited.json()["draft"]["declarations"]).lower()

    recalculated = client.post(f"/api/claims/{claim['id']}/recalculate")
    assert recalculated.status_code == 200
    assert recalculated.json()["draft"]["financials"]["itemized_total"] == "98750.00"

    review = client.post(f"/api/claims/{claim['id']}/draft/review", json={"confirmed": True})
    assert review.status_code == 200
    ready = client.post(f"/api/claims/{claim['id']}/ready", json={"confirmed": False})
    assert ready.status_code == 400
    ready = client.post(f"/api/claims/{claim['id']}/ready", json={"confirmed": True})
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready_for_submission"
    assert "not" in ready.json()["notice"].lower()

    reopened = client.get(f"/api/claims/{claim['id']}")
    assert reopened.json()["status"] == "ready_for_submission"

    pdf = client.get(f"/api/claims/{claim['id']}/export/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "NOT SUBMITTED" in text
    assert "FICTIONAL" in text
    assert "Claim-It provides AI-assisted" in text

    exported = client.get(f"/api/claims/{claim['id']}/export/json")
    assert exported.status_code == 200
    assert exported.json()["demo_mode"] is True
    assert "not submitted" in exported.json()["export_note"].lower()

    csv = client.get(f"/api/claims/{claim['id']}/export/checklist.csv")
    assert csv.status_code == 200
    body = csv.content.decode()
    assert "document_name,reason,status,source,source_reference" in body
    assert "Cancelled cheque or bank statement" in body

    question = client.post(f"/api/claims/{claim['id']}/ask", json={"question": "What does the room rent clause say?"})
    assert question.status_code == 200
    payload = question.json()
    assert payload["live_api_call"] is False
    assert payload["engine"] == "demo"
    assert any(citation["page_number"] == 2 for citation in payload["citations"])

    listed = client.get("/api/claims")
    assert any(item["id"] == claim["id"] for item in listed.json()["claims"])
    deleted = client.delete(f"/api/claims/{claim['id']}")
    assert deleted.status_code == 200
    missing = client.get(f"/api/claims/{claim['id']}")
    assert missing.status_code == 404


def test_upload_sample_without_api_key_uses_local_text(client, tmp_path):
    created = client.post(
        "/api/claims",
        json={
            "nickname": "Manual sample",
            "claim_type": "health",
            "policyholder_name": "Ananya Sharma",
            "incident_date": "2026-10-12",
            "claim_type_detail": "reimbursement",
            "language": "en",
        },
    )
    assert created.status_code == 200
    claim_id = created.json()["id"]
    assert created.json()["demo_mode"] is False
    paths = ensure_sample_documents(tmp_path)
    for key, document_type in (
        ("policy", "policy"),
        ("discharge", "discharge_summary"),
        ("bill", "bill"),
        ("pharmacy", "bill"),
    ):
        content = paths[key].read_bytes()
        response = client.post(
            f"/api/claims/{claim_id}/documents",
            data={"document_type": document_type},
            files={"file": (paths[key].name, content, "application/pdf")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["processing_engine"] == "local_text"
        assert body["live_api_call"] is False
        assert body["processing_status"] == "completed"

    narrative = client.post(
        f"/api/claims/{claim_id}/narrative",
        json={
            "transcript": "My father was admitted on 12 October 2026 and discharged on 15 October 2026.",
            "confirm": True,
            "language": "en",
            "source": "text",
        },
    )
    assert narrative.status_code == 200
    analysed = client.post(f"/api/claims/{claim_id}/analyze")
    assert analysed.status_code == 200
    body = analysed.json()
    assert body["analysis"]["engine"] == "deterministic"
    assert body["analysis"]["live_api_call"] is False
    assert body["status"] == "analysis_complete"
    assert body["analysis"]["financials"]["difference"] == "750.00"
    draft = client.post(f"/api/claims/{claim_id}/draft")
    assert draft.status_code == 200
    assert "Claim-It provides AI-assisted" in draft.json()["draft"]["warning"]

    speech = client.post(
        f"/api/claims/{claim_id}/transcribe",
        data={"language": "hi"},
        files={"audio": ("note.wav", b"RIFFfake", "audio/wav")},
    )
    assert speech.status_code == 503
    assert speech.json()["error"]["code"] == "missing_api_key"

    image = client.post(
        f"/api/claims/{claim_id}/documents",
        data={"document_type": "other"},
        files={"file": ("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png")},
    )
    assert image.status_code == 200
    assert image.json()["processing_status"] == "failed"
    assert "not called" in image.json()["error_message"].lower()


def test_database_crud_and_motor_placeholder(client):
    denied = client.post("/api/claims", json={"nickname": "Car", "claim_type": "motor"})
    assert denied.status_code == 400
    bad = client.post("/api/claims", json={"nickname": "Bad date", "incident_date": "12/10/2026"})
    assert bad.status_code == 422
    created = client.post("/api/claims", json={"nickname": "Asha", "language": "hi"})
    claim_id = created.json()["id"]
    patched = client.patch(f"/api/claims/{claim_id}", json={"insurer_name": "Example Cover"})
    assert patched.json()["insurer_name"] == "Example Cover"
    assert patched.json()["language"] == "hi"
    wiped = client.delete("/api/data")
    assert wiped.status_code == 200
    assert client.get("/api/claims").json()["claims"] == []
