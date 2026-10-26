"""Shared Sarvam client construction and error mapping."""

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError, SarvamTimeoutError


def request_options(timeout: int) -> dict:
    return {"timeout_in_seconds": timeout, "max_retries": 0}


def build_client(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.sarvam_configured:
        return None
    try:
        from sarvamai import SarvamAI
    except ImportError as exc:
        raise AppError(500, "sarvam_sdk_missing", "The Sarvam Python SDK is not installed.") from exc
    return SarvamAI(api_subscription_key=settings.sarvam_api_key.strip(), timeout=float(settings.sarvam_timeout_seconds))


def map_sarvam_error(exc: Exception) -> None:
    """Translate SDK failures. The original body is not returned, so document text cannot leak."""
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, SarvamTimeoutError)):
        raise SarvamTimeoutError("Sarvam did not respond before the timeout. Try again in a moment.") from exc
    status = getattr(exc, "status_code", None)
    name = exc.__class__.__name__.lower()
    if "timeout" in name:
        raise SarvamTimeoutError("Sarvam did not respond before the timeout. Try again in a moment.") from exc
    if status == 429:
        raise AppError(429, "rate_limited", "Sarvam rate limit reached. Wait a moment and try again.") from exc
    if status == 402:
        raise AppError(402, "insufficient_quota", "Sarvam accepted the key, but this account has no credits left.") from exc
    if status in {401, 403}:
        raise AppError(502, "sarvam_auth", "Sarvam rejected the API key. Check SARVAM_API_KEY on the server.") from exc
    raise AppError(502, "sarvam_error", "Sarvam could not complete the request. Your documents were not changed.") from exc
