"""Sarvam Vision through the Document AI digitise and extract jobs."""

import io
import time

from app.core.config import get_settings
from app.core.errors import MissingCredentialsError, SarvamJobError, SarvamTimeoutError
from app.services.extraction import SPECS_BY_TYPE
from app.services.sarvam_client import map_sarvam_error, request_options
from app.services.textutil import normalize_ws

TERMINAL = {"completed", "partially_completed", "failed", "rejected"}


def schema_for(document_type: str) -> dict:
    specs = SPECS_BY_TYPE.get(document_type, SPECS_BY_TYPE["other"])
    properties = {}
    seen = set()
    for key, label, _pattern in specs:
        if key in seen:
            continue
        seen.add(key)
        properties[key] = {
            "type": "string",
            "description": f"{label} exactly as printed in the document. Use an empty string when it is not present. Do not guess.",
        }
    return {"type": "object", "properties": properties}


def _status_of(payload) -> str:
    if isinstance(payload, dict):
        return str(payload.get("status") or "").lower()
    return str(getattr(payload, "status", "") or "").lower()


def _job_id(payload) -> str:
    if isinstance(payload, dict):
        return str(payload["job_id"])
    return str(payload.job_id)


def poll_job(client, job_id: str, timeout: int, sleeper=time.sleep) -> str:
    deadline = time.monotonic() + timeout
    while True:
        try:
            status = client.doc_ai.get_status(job_id, request_options=request_options(timeout))
        except Exception as exc:
            map_sarvam_error(exc)
            raise
        state = _status_of(status)
        if state in TERMINAL:
            return state
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SarvamTimeoutError("The Sarvam Vision job did not finish before the timeout.")
        sleeper(min(2.0, remaining))


def _file_arg(filename: str, content: bytes, mime: str):
    return [(filename, io.BytesIO(content), mime)]


def digitise(client, filename: str, content: bytes, mime: str, language: str, sleeper=time.sleep) -> dict:
    if client is None:
        raise MissingCredentialsError("Sarvam Vision needs SARVAM_API_KEY. No document was sent.")
    settings = get_settings()
    code = "hi-IN" if language == "hi" else "en-IN"
    try:
        job = client.doc_ai.digitise(
            file=_file_arg(filename, content, mime),
            language=code,
            request_options=request_options(settings.sarvam_timeout_seconds),
        )
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    job_id = _job_id(job)
    state = poll_job(client, job_id, settings.doc_job_timeout_seconds, sleeper=sleeper)
    if state in {"failed", "rejected"}:
        raise SarvamJobError(state, "Sarvam Vision could not read this document. Try a clearer PDF or image.")
    try:
        results = client.doc_ai.get_results(job_id, format="md", request_options=request_options(settings.sarvam_timeout_seconds))
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    pages = _pages_from_digitise(results)
    return {"job_id": job_id, "status": state, "pages": pages}


def extract(client, filename: str, content: bytes, mime: str, document_type: str, sleeper=time.sleep) -> dict:
    if client is None:
        raise MissingCredentialsError("Sarvam Vision needs SARVAM_API_KEY. No document was sent.")
    settings = get_settings()
    import json

    try:
        job = client.doc_ai.extract(
            file=_file_arg(filename, content, mime),
            schema=json.dumps(schema_for(document_type)),
            output_format="json",
            request_options=request_options(settings.sarvam_timeout_seconds),
        )
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    job_id = _job_id(job)
    state = poll_job(client, job_id, settings.doc_job_timeout_seconds, sleeper=sleeper)
    if state in {"failed", "rejected"}:
        raise SarvamJobError(state, "Sarvam Vision rejected or failed this document before fields could be saved.")
    try:
        results = client.doc_ai.get_results(job_id, request_options=request_options(settings.sarvam_timeout_seconds))
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    result = getattr(results, "result", None)
    annotations = getattr(results, "annotations", None)
    if isinstance(results, dict):
        result = results.get("result")
        annotations = results.get("annotations")
    if not isinstance(result, dict):
        result = {}
    if not isinstance(annotations, dict):
        annotations = {}
    return {"job_id": job_id, "status": state, "result": result, "annotations": annotations}


def _pages_from_digitise(results) -> list[dict]:
    documents = getattr(results, "documents", None)
    if isinstance(results, dict):
        documents = results.get("documents")
    pages = []
    for document in documents or []:
        doc_pages = document.get("pages") if isinstance(document, dict) else getattr(document, "pages", None)
        for page in doc_pages or []:
            number = page.get("page_number") if isinstance(page, dict) else getattr(page, "page_number", None)
            content = page.get("content") if isinstance(page, dict) else getattr(page, "content", None)
            if number is None:
                continue
            pages.append({"page_number": int(number), "text": normalize_ws(content or "")})
    pages.sort(key=lambda item: item["page_number"])
    return pages
