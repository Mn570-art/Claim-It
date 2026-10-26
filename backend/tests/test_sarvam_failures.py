from types import SimpleNamespace

import httpx
import pytest

from app.core.errors import InvalidModelOutputError, SarvamTimeoutError
from app.services.sarvam_chat import complete_json
from app.services.sarvam_client import map_sarvam_error
from app.services.sarvam_vision import poll_job


class Boom(Exception):
    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__("status only")


def test_timeout_and_rate_limit_mapping():
    with pytest.raises(SarvamTimeoutError):
        map_sarvam_error(TimeoutError())
    with pytest.raises(SarvamTimeoutError):
        map_sarvam_error(httpx.TimeoutException("slow"))
    with pytest.raises(Exception) as rate:
        map_sarvam_error(Boom(429))
    assert rate.value.status_code == 429
    assert rate.value.code == "rate_limited"
    with pytest.raises(Exception) as auth:
        map_sarvam_error(Boom(401))
    assert auth.value.code == "sarvam_auth"


def test_invalid_model_output_is_repaired_once_then_rejected():
    calls = {"n": 0}

    class Chat:
        def completions(self, **kwargs):
            calls["n"] += 1
            content = "not-json" if calls["n"] == 1 else "{}"
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    class Client:
        chat = Chat()

    with pytest.raises(InvalidModelOutputError):
        complete_json(Client(), [{"role": "user", "content": "analyse"}])
    assert calls["n"] == 2


def test_vision_job_timeout(monkeypatch):
    class Doc:
        def get_status(self, job_id, request_options=None):
            return SimpleNamespace(status="running")

    class Client:
        doc_ai = Doc()

    with pytest.raises(SarvamTimeoutError):
        poll_job(Client(), "job-1", timeout=0, sleeper=lambda _seconds: None)


def test_analyze_falls_back_when_model_output_is_invalid(client):
    class Chat:
        def completions(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="nope"))])

    class Client:
        chat = Chat()

    client.app.state.sarvam_client_factory = lambda: Client()
    from app.core.config import get_settings

    get_settings.cache_clear()
    # The app reads the key only when building the default client. This test injects one.
    created = client.post(
        "/api/claims",
        json={"nickname": "Fallback", "claim_type_detail": "reimbursement", "incident_date": "2026-10-12"},
    )
    claim_id = created.json()["id"]
    analysed = client.post(f"/api/claims/{claim_id}/analyze")
    assert analysed.status_code == 200
    body = analysed.json()
    assert body["analysis"]["engine"] == "deterministic"
    assert body["analysis"]["live_api_call"] is True
    assert "invalid" in body["analysis"]["note"].lower()


def test_demo_seed_does_not_call_injected_client(client):
    called = {"n": 0}

    def factory():
        called["n"] += 1
        raise AssertionError("demo mode must not construct a Sarvam client")

    client.app.state.sarvam_client_factory = factory
    response = client.post("/api/demo/seed?stage=ready")
    assert response.status_code == 200
    assert response.json()["analysis"]["live_api_call"] is False
    assert called["n"] == 0
