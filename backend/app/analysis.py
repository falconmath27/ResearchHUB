from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader


MAX_ANALYSIS_PAGES = 200
MAX_EXTRACTED_CHARACTERS = 500_000


@dataclass
class AnalysisExtractionError(Exception):
    code: str
    public_message: str


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _bounded_result(text: str, *, file_type: str, page_count: int | None) -> dict[str, object]:
    cleaned = _clean_text(text)
    if len(cleaned) < 20:
        raise AnalysisExtractionError(
            "no_extractable_text",
            "No usable text could be extracted from this file.",
        )

    truncated = len(cleaned) > MAX_EXTRACTED_CHARACTERS
    extracted = cleaned[:MAX_EXTRACTED_CHARACTERS]
    return {
        "stage": "extraction_complete",
        "file_type": file_type,
        "page_count": page_count,
        "character_count": len(cleaned),
        "word_count": len(cleaned.split()),
        "truncated": truncated,
        "text": extracted,
        "text_preview": extracted[:1_000],
    }


def extract_attachment_text(file_path: Path) -> dict[str, object]:
    if not file_path.is_file():
        raise AnalysisExtractionError(
            "attachment_missing",
            "The uploaded file is no longer available.",
        )

    extension = file_path.suffix.lower()
    if extension == ".txt":
        try:
            text = file_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as error:
            raise AnalysisExtractionError(
                "invalid_text_encoding",
                "The text file must use UTF-8 encoding.",
            ) from error
        return _bounded_result(text, file_type="txt", page_count=None)

    if extension == ".pdf":
        try:
            reader = PdfReader(file_path)
            if reader.is_encrypted:
                raise AnalysisExtractionError(
                    "encrypted_pdf",
                    "Encrypted PDFs cannot be analyzed.",
                )
            if len(reader.pages) > MAX_ANALYSIS_PAGES:
                raise AnalysisExtractionError(
                    "page_limit_exceeded",
                    f"PDFs are limited to {MAX_ANALYSIS_PAGES} pages for analysis.",
                )
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except AnalysisExtractionError:
            raise
        except Exception as error:
            raise AnalysisExtractionError(
                "invalid_pdf",
                "The PDF could not be read safely.",
            ) from error
        return _bounded_result(text, file_type="pdf", page_count=len(reader.pages))

    raise AnalysisExtractionError(
        "unsupported_file_type",
        "Analysis currently supports PDF and TXT files only.",
    )
