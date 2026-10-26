"""Consistent API errors. Document contents are never attached to these messages."""


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class MissingCredentialsError(AppError):
    def __init__(self, message: str = "SARVAM_API_KEY is not configured. Type the description instead, or open Demo Mode."):
        super().__init__(503, "missing_api_key", message)


class SarvamTimeoutError(AppError):
    def __init__(self, message: str = "Sarvam did not respond before the timeout."):
        super().__init__(504, "sarvam_timeout", message)


class SarvamJobError(AppError):
    def __init__(self, status: str, message: str):
        code = "sarvam_rejected" if status == "rejected" else "sarvam_failed"
        super().__init__(422, code, message, {"job_status": status})


class InvalidModelOutputError(AppError):
    def __init__(self, message: str = "The model returned data that did not match the required schema."):
        super().__init__(502, "invalid_model_output", message)
