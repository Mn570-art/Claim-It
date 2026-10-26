"""Request bodies."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _date(value: str | None) -> str | None:
    value = _blank(value)
    if value is None:
        return None
    datetime.strptime(value, "%Y-%m-%d")
    return value


class ClaimCreate(BaseModel):
    nickname: str = ""
    claim_type: str = "health"
    insurer_name: str | None = None
    policyholder_name: str | None = None
    policy_number: str | None = None
    incident_date: str | None = None
    claim_type_detail: str | None = None
    language: str = "en"
    patient_name: str | None = None
    hospital_name: str | None = None

    @field_validator("claim_type")
    @classmethod
    def claim_type_ok(cls, value: str) -> str:
        if value not in {"health", "motor"}:
            raise ValueError("claim_type must be health or motor")
        return value

    @field_validator("claim_type_detail")
    @classmethod
    def detail_ok(cls, value: str | None) -> str | None:
        value = _blank(value)
        if value and value not in {"cashless", "reimbursement"}:
            raise ValueError("claim_type_detail must be cashless, reimbursement, or empty")
        return value

    @field_validator("language")
    @classmethod
    def language_ok(cls, value: str) -> str:
        if value not in {"en", "hi"}:
            raise ValueError("language must be en or hi")
        return value

    @field_validator("incident_date")
    @classmethod
    def date_ok(cls, value: str | None) -> str | None:
        try:
            return _date(value)
        except ValueError as exc:
            raise ValueError("incident_date must be YYYY-MM-DD") from exc

    @field_validator("nickname", "insurer_name", "policyholder_name", "policy_number", "patient_name", "hospital_name")
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        return _blank(value) if value is not None else None


class ClaimPatch(ClaimCreate):
    nickname: str | None = None
    claim_type: str | None = None
    language: str | None = None

    @field_validator("claim_type")
    @classmethod
    def claim_type_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in {"health", "motor"}:
            raise ValueError("claim_type must be health or motor")
        return value

    @field_validator("language")
    @classmethod
    def language_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in {"en", "hi"}:
            raise ValueError("language must be en or hi")
        return value


class NarrativeIn(BaseModel):
    transcript: str = ""
    confirmed_transcript: str | None = None
    language: str = "en"
    source: str = "text"
    confirm: bool = True

    @field_validator("language")
    @classmethod
    def language_ok(cls, value: str) -> str:
        if value not in {"en", "hi"}:
            raise ValueError("language must be en or hi")
        return value

    @field_validator("source")
    @classmethod
    def source_ok(cls, value: str) -> str:
        if value not in {"text", "voice", "demo"}:
            raise ValueError("source must be text, voice, or demo")
        return value


class QuestionIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    language: str = "en"


class ConfirmIn(BaseModel):
    confirmed: bool


class SettingsPatch(BaseModel):
    preferred_language: str | None = None
    voice_playback: bool | None = None

    @field_validator("preferred_language")
    @classmethod
    def language_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in {"en", "hi"}:
            raise ValueError("preferred_language must be en or hi")
        return value


class DraftPatch(BaseModel):
    policyholder_name: str | None = None
    insurer_name: str | None = None
    policy_number: str | None = None
    patient_name: str | None = None
    patient_name_on_discharge: str | None = None
    hospital_name: str | None = None
    incident_narrative: str | None = None
    incident_date: str | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    diagnosis: str | None = None
    procedure: str | None = None
    treatment: str | None = None
    expenses: list[dict] | None = None
    amount_claimed: str | None = None
    printed_total: str | None = None
    supporting_documents: list[str] | None = None
    missing_documents: list[str] | None = None
    unresolved_questions: list[str] | None = None
    declarations: list[str] | None = None
