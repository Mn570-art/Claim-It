"""Upload validation. Files stay on local disk and are never given a public URL."""

import io
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import AppError

ALLOWED_EXTENSIONS = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_FILENAME = 180


def _extension(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix


def detect_mime(content: bytes, filename: str) -> str:
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            400,
            "unsupported_type",
            "Upload a PDF, PNG, JPG, or JPEG file.",
        )
    if content.startswith(b"%PDF"):
        detected = "application/pdf"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    else:
        raise AppError(
            400,
            "unreadable_document",
            "This file could not be read. It is not a valid PDF, PNG, or JPEG.",
        )
    expected = ALLOWED_EXTENSIONS[ext]
    if detected != expected:
        raise AppError(
            400,
            "type_mismatch",
            "The file contents do not match its extension.",
        )
    return detected


def page_count(content: bytes, mime: str) -> int:
    if mime != "application/pdf":
        return 1
    try:
        reader = PdfReader(io.BytesIO(content))
        count = len(reader.pages)
    except (PdfReadError, Exception) as exc:
        raise AppError(
            400,
            "unreadable_document",
            "This PDF could not be opened. It may be damaged or password protected.",
        ) from exc
    if count < 1:
        raise AppError(400, "unreadable_document", "This PDF has no pages.")
    return count


def validate_upload(filename: str, content: bytes, max_mb: int, max_pages: int) -> dict:
    if not filename or not filename.strip():
        raise AppError(400, "missing_filename", "Choose a file to upload.")
    if len(content) == 0:
        raise AppError(400, "empty_file", "The file is empty.")
    limit = max_mb * 1024 * 1024
    if len(content) > limit:
        raise AppError(400, "file_too_large", f"Each file must be {max_mb} MB or smaller.")
    mime = detect_mime(content, filename)
    pages = page_count(content, mime)
    if mime == "application/pdf" and pages > max_pages:
        raise AppError(
            400,
            "too_many_pages",
            f"PDFs are limited to {max_pages} pages. Split this file and upload the relevant pages.",
        )
    safe_name = Path(filename).name.replace("\x00", "")[:MAX_FILENAME]
    return {"filename": safe_name, "mime_type": mime, "size_bytes": len(content), "page_count": pages}


def extract_pdf_pages(content: bytes) -> list[dict]:
    try:
        reader = PdfReader(io.BytesIO(content))
    except (PdfReadError, Exception) as exc:
        raise AppError(400, "unreadable_document", "This PDF could not be read.") from exc
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page_number": index, "text": text})
    return pages


def safe_storage_path(root: Path, claim_id: str, document_id: str, filename: str) -> Path:
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        ext = ""
    folder = (root / claim_id).resolve()
    if not str(folder).startswith(str(root.resolve())):
        raise AppError(400, "invalid_path", "The storage path is not allowed.")
    folder.mkdir(parents=True, exist_ok=True)
    destination = (folder / f"{document_id}{ext}").resolve()
    if not str(destination).startswith(str(root.resolve())):
        raise AppError(400, "invalid_path", "The storage path is not allowed.")
    return destination
