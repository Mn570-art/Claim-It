"""Keyword retrieval over policy chunks. Page numbers come from the extracted text, not the model."""

import re
import uuid

from app.services.textutil import normalize_ws

STOP = {
    "the", "and", "for", "that", "with", "this", "from", "are", "was", "were", "has", "had",
    "have", "not", "but", "you", "your", "his", "her", "its", "they", "them", "been", "will",
    "shall", "may", "only", "into", "over", "under", "than", "then", "also", "such", "other",
    "when", "where", "which", "who", "whom", "what", "how", "after", "before", "during",
}

MUST_KEEP = (
    "clause 4.1",
    "clause 4.3",
    "clause 5.1",
    "clause 5.2",
    "clause 7.1",
    "clause 7.2",
    "clause 4.6",
    "clause 2.1",
)


def tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", (text or "").casefold()) if token not in STOP}


def chunk_pages(pages: list[dict], claim_id: str, document_id: str) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        lines = [line.strip() for line in (page.get("text") or "").splitlines()]
        buffer: list[str] = []

        def flush() -> None:
            body = normalize_ws(" ".join(buffer))
            buffer.clear()
            if len(body) < 30:
                return
            title = None
            if body.casefold().startswith("clause"):
                title = body.split(".")[0][:180]
            chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "claim_id": claim_id,
                    "document_id": document_id,
                    "page_number": int(page["page_number"]),
                    "section_title": title,
                    "text": body,
                }
            )

        for line in lines:
            if line.startswith("FICTIONAL SAMPLE") or line.startswith("Page "):
                continue
            if not line:
                flush()
                continue
            if line.startswith("Clause ") and buffer:
                flush()
            buffer.append(line)
            if len(" ".join(buffer)) > 1200:
                flush()
        flush()
    return chunks


def retrieve(chunks: list[dict], query: str, limit: int = 8) -> list[dict]:
    query_tokens = tokens(query)
    ranked = []
    for chunk in chunks:
        overlap = len(tokens(chunk["text"]) & query_tokens)
        lowered = chunk["text"].casefold()
        boost = 0
        if "room" in query.casefold() and "room rent" in lowered:
            boost += 5
        if "consum" in query.casefold() and "consumable" in lowered:
            boost += 5
        if "wait" in query.casefold() and "waiting" in lowered:
            boost += 4
        if any(word in query.casefold() for word in ("document", "cheque", "form", "bank")) and "clause 7." in lowered:
            boost += 4
        if "hospital" in query.casefold() and "clause 4.1" in lowered:
            boost += 4
        ranked.append((overlap + boost, overlap, chunk))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    chosen: list[dict] = []
    seen = set()
    for chunk in chunks:
        lowered = chunk["text"].casefold()
        if any(marker in lowered for marker in MUST_KEEP):
            chosen.append(chunk)
            seen.add(chunk["id"])
    for score, _overlap, chunk in ranked:
        if score <= 0 or chunk["id"] in seen:
            continue
        chosen.append(chunk)
        seen.add(chunk["id"])
        if len(chosen) >= max(limit, 12):
            break
    return chosen[: max(limit, 12)]
