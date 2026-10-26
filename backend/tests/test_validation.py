from reportlab.pdfgen import canvas

from app.core.errors import AppError
from app.services.files import validate_upload


def _pdf(path, pages: int) -> bytes:
    pdf = canvas.Canvas(str(path))
    for index in range(pages):
        pdf.drawString(72, 720, f"Page {index + 1} fictional text for validation.")
        pdf.showPage()
    pdf.save()
    return path.read_bytes()


def test_rejects_unknown_type_and_empty(tmp_path):
    with pytest_raises_app(400, "unsupported_type"):
        validate_upload("notes.txt", b"hello", 10, 20)
    with pytest_raises_app(400, "empty_file"):
        validate_upload("scan.pdf", b"", 10, 20)


def test_rejects_mismatched_magic_and_oversize(tmp_path):
    with pytest_raises_app(400, "unreadable_document"):
        validate_upload("scan.pdf", b"not a pdf", 10, 20)
    big = b"%PDF" + b"x" * (2 * 1024 * 1024)
    with pytest_raises_app(400, "file_too_large"):
        validate_upload("scan.pdf", big, 1, 20)


def test_rejects_too_many_pages_and_accepts_a_short_pdf(tmp_path):
    long_pdf = _pdf(tmp_path / "long.pdf", 21)
    with pytest_raises_app(400, "too_many_pages"):
        validate_upload("long.pdf", long_pdf, 10, 20)
    short = _pdf(tmp_path / "short.pdf", 2)
    checked = validate_upload("short.pdf", short, 10, 20)
    assert checked["mime_type"] == "application/pdf"
    assert checked["page_count"] == 2


def test_accepts_jpeg_magic():
    content = b"\xff\xd8\xff" + b"\x00" * 32
    checked = validate_upload("photo.jpg", content, 10, 20)
    assert checked["mime_type"] == "image/jpeg"
    assert checked["page_count"] == 1


def pytest_raises_app(status, code):
    import pytest

    class _Expect:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            assert exc_type is AppError
            assert exc.status_code == status
            assert exc.code == code
            return True

    return _Expect()
