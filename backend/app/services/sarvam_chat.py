"""Sarvam-105B structured claim analysis. Invalid JSON is rejected, then repaired once."""

import json
import re

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.core.errors import InvalidModelOutputError, MissingCredentialsError
from app.services.sarvam_client import map_sarvam_error, request_options

CATEGORIES = ["potentially_supported", "potentially_excluded", "uncertain", "missing_information"]

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "policy_source": {"type": "string"},
                    "policy_clause": {"type": "string"},
                    "page_number": {"type": "integer"},
                    "claim_evidence": {"type": "array", "items": {"type": "string"}},
                    "missing_information": {"type": "array", "items": {"type": "string"}},
                    "recommended_next_step": {"type": "string"},
                },
                "required": [
                    "category",
                    "title",
                    "explanation",
                    "policy_source",
                    "policy_clause",
                    "page_number",
                    "claim_evidence",
                    "missing_information",
                    "recommended_next_step",
                ],
            },
        },
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "overall_status": {"type": "string", "enum": ["needs_review", "ready_for_user_review"]},
    },
    "required": ["summary", "findings", "follow_up_questions", "overall_status"],
}


class ModelFinding(BaseModel):
    category: str
    title: str = Field(min_length=1, max_length=300)
    explanation: str
    policy_source: str = ""
    policy_clause: str = ""
    page_number: int = 0
    claim_evidence: list[str] = []
    missing_information: list[str] = []
    recommended_next_step: str = ""


class ModelAnalysis(BaseModel):
    summary: str
    findings: list[ModelFinding]
    follow_up_questions: list[str]
    overall_status: str


def parse_model_payload(raw: str) -> ModelAnalysis:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidModelOutputError("The model did not return valid JSON.") from exc
    try:
        parsed = ModelAnalysis.model_validate(data)
    except ValidationError as exc:
        raise InvalidModelOutputError("The model JSON did not match the claim-analysis schema.") from exc
    if parsed.overall_status not in {"needs_review", "ready_for_user_review"}:
        raise InvalidModelOutputError("The model returned an unknown overall status.")
    if any(item.category not in CATEGORIES for item in parsed.findings):
        raise InvalidModelOutputError("The model returned an unknown finding category.")
    return parsed


def _content_from(response) -> str:
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"]
    return response.choices[0].message.content


def complete_json(client, messages: list[dict]) -> ModelAnalysis:
    if client is None:
        raise MissingCredentialsError("Sarvam-105B needs SARVAM_API_KEY. No prompt was sent.")
    settings = get_settings()
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "claim_analysis", "strict": True, "schema": ANALYSIS_SCHEMA},
    }

    def call(prompt_messages: list[dict]):
        try:
            return client.chat.completions(
                model="sarvam-105b",
                messages=prompt_messages,
                temperature=0.2,
                reasoning_effort="low",
                max_tokens=4096,
                response_format=response_format,
                request_options=request_options(settings.sarvam_timeout_seconds),
            )
        except Exception as exc:
            map_sarvam_error(exc)
            raise

    first = call(messages)
    try:
        return parse_model_payload(_content_from(first))
    except InvalidModelOutputError as first_error:
        repair = messages + [
            {"role": "assistant", "content": _content_from(first)[:4000]},
            {
                "role": "user",
                "content": (
                    "That response failed validation. Return only JSON matching the schema. "
                    "Do not invent policy wording, page numbers, or amounts. "
                    f"Validation error: {first_error.message}"
                ),
            },
        ]
        second = call(repair)
        try:
            return parse_model_payload(_content_from(second))
        except InvalidModelOutputError as exc:
            raise InvalidModelOutputError(
                "Sarvam-105B returned invalid structured output twice. It was not used as a conclusion."
            ) from exc


def analysis_messages(language: str, excerpts: list[dict], facts: dict, financials: dict, narrative: str) -> list[dict]:
    language_name = "Hindi" if language == "hi" else "English"
    system = (
        "You help prepare an Indian health-insurance claim. You do not decide coverage, promise reimbursement, "
        "or invent policy wording, page numbers, diagnoses, or amounts. "
        "Quote policy_clause only as an exact substring of a provided excerpt. If you cannot quote one, use an empty policy_clause and page_number 0. "
        "Use page_number 0 when you are not citing a clause. Categories: potentially_supported, potentially_excluded, uncertain, missing_information. "
        "potentially_excluded means a specific limitation may apply, not that the claim is rejected. "
        "Use the supplied financial figures as given. Do not recompute them. "
        f"Write summary, titles, explanations, and questions in {language_name}."
    )
    payload = {
        "excerpts": [
            {
                "document_id": item["document_id"],
                "page_number": item["page_number"],
                "text": item["text"],
            }
            for item in excerpts
        ],
        "narrative": narrative,
        "facts": facts,
        "financials": financials,
    }
    user = (
        "Compare the claim facts with these policy excerpts only. "
        "Return findings a claimant should review. Do not say a sum is payable.\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


ASK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "quote": {"type": "string"},
                    "page_number": {"type": "integer"},
                },
                "required": ["quote", "page_number"],
            },
        },
    },
    "required": ["answer", "quotes"],
}


class ModelAnswer(BaseModel):
    answer: str
    quotes: list[dict]


def answer_question(client, language: str, question: str, excerpts: list[dict]) -> dict:
    if client is None:
        raise MissingCredentialsError("Sarvam-105B needs SARVAM_API_KEY. No question was sent.")
    settings = get_settings()
    language_name = "Hindi" if language == "hi" else "English"
    messages = [
        {
            "role": "system",
            "content": (
                "Answer only from the policy excerpts. If they do not answer the question, say that no conclusion was established. "
                "quotes must be exact substrings. Use page_number 0 when you have no quote. "
                f"Write the answer in {language_name}. Do not promise reimbursement."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"question": question, "excerpts": excerpts}, ensure_ascii=False),
        },
    ]
    try:
        response = client.chat.completions(
            model="sarvam-105b",
            messages=messages,
            temperature=0.2,
            reasoning_effort="low",
            max_tokens=1500,
            response_format={"type": "json_schema", "json_schema": {"name": "clause_answer", "strict": True, "schema": ASK_SCHEMA}},
            request_options=request_options(settings.sarvam_timeout_seconds),
        )
    except Exception as exc:
        map_sarvam_error(exc)
        raise
    try:
        data = json.loads(_content_from(response))
        answer = str(data.get("answer") or "").strip()
        quotes = data.get("quotes") if isinstance(data.get("quotes"), list) else []
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise InvalidModelOutputError("Sarvam-105B did not return a valid answer.") from exc
    if not answer:
        raise InvalidModelOutputError("Sarvam-105B returned an empty answer.")
    return {"answer": answer, "quotes": quotes}


def model_to_findings(parsed: ModelAnalysis) -> list[dict]:
    findings = []
    for item in parsed.findings:
        findings.append(
            {
                "code": "model",
                "category": item.category,
                "title": item.title.strip(),
                "explanation": item.explanation.strip(),
                "policy_clause": item.policy_clause.strip() or None,
                "policy_source": item.policy_source.strip() or None,
                "source_document_id": None,
                "source_page": item.page_number or None,
                "page_number": item.page_number or None,
                "supporting_evidence": item.claim_evidence,
                "missing_information": item.missing_information,
                "recommended_next_step": item.recommended_next_step.strip(),
                "review_status": "needs_review",
                "citation_status": "unverified",
            }
        )
    return findings
