from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from .config import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES, UPLOAD_DIRECTORY


async def save_upload(upload: UploadFile) -> tuple[str, str, int, str | None]:
    original_filename = Path(upload.filename or "").name
    extension = Path(original_filename).suffix.lower()
    content_type = upload.content_type

    if not original_filename or extension not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(status_code=422, detail=f"Allowed file types: {allowed}")

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIRECTORY / stored_filename
    size_bytes = 0

    try:
        with destination.open("xb") as output_file:
            while chunk := await upload.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 20 MB upload limit.",
                    )
                output_file.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return original_filename, stored_filename, size_bytes, content_type


def attachment_file_path(stored_filename: str) -> Path:
    return UPLOAD_DIRECTORY / stored_filename


def delete_upload(stored_filename: str) -> None:
    attachment_file_path(stored_filename).unlink(missing_ok=True)
