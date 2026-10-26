"""Small text helpers shared by extraction, retrieval, and citation checks."""

import re
import unicodedata


def normalize_ws(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_match(value: str) -> str:
    return normalize_ws(value).casefold()


def is_missing_token(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        token = normalize_match(value)
        return token in {"", "null", "none", "n/a", "na", "not found", "not available", "-", "—", "unknown"}
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def stringify(value: object) -> str | None:
    if is_missing_token(value):
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    text = str(value).strip()
    return None if is_missing_token(text) else text
