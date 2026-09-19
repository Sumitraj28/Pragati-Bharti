from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, UploadFile, status

from app.storage.local_storage import save_file

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def validate_file_content(filename: str, content: bytes) -> str:
    """
    Validates file extension, size, and magic byte signature.
    Returns the detected MIME content type or raises HTTPException(400).
    """
    if not filename or "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required with a valid extension.",
        )

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Only pdf, jpg, jpeg, and png are allowed.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 20MB limit.",
        )

    # Magic byte inspection
    detected_mime = None
    if content.startswith(b"%PDF-"):
        detected_mime = "application/pdf"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"

    if not detected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file signature (magic bytes mismatch). File is not a valid PDF, JPG, or PNG.",
        )

    # Check extension compatibility with detected mime
    expected_mime = ALLOWED_EXTENSIONS[ext]
    if detected_mime != expected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' does not match file content type '{detected_mime}'.",
        )

    return detected_mime
