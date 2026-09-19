import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Union

# Base upload directory
UPLOAD_DIR = Path("uploads")


class StorageBackend(ABC):
    """
    Abstract StorageBackend interface.

    This interface defines the contract for document file storage operations.
    In the current implementation, LocalStorage stores documents on the local filesystem.
    This abstraction allows easily swapping the backend for cloud object storage
    (such as AWS S3, Google Cloud Storage, Cloudflare R2, or Azure Blob Storage)
    in production environments without altering application services or routes.
    """

    @abstractmethod
    def save_file(self, file_content: bytes, original_filename: str) -> str:
        """Save file bytes and return a unique storage path."""
        pass

    @abstractmethod
    def get_file(self, storage_path: str) -> bytes:
        """Retrieve file bytes by its storage path."""
        pass


class LocalStorage(StorageBackend):
    """Local disk storage implementation using UUID-based filenames to avoid path traversal."""

    def __init__(self, base_dir: Union[str, Path] = UPLOAD_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_content: bytes, original_filename: str = "") -> str:
        """
        Saves file content with a randomized UUID filename.
        Never trusts user-supplied filenames for the filesystem path.
        """
        # Extract extension safely
        ext = ""
        if original_filename and "." in original_filename:
            ext = f".{original_filename.rsplit('.', 1)[-1].lower()}"

        unique_filename = f"{uuid.uuid4().hex}{ext}"
        destination = self.base_dir / unique_filename

        with open(destination, "wb") as f:
            f.write(file_content)

        return str(destination)

    def get_file(self, storage_path: str) -> bytes:
        """Reads and returns file bytes from local disk."""
        path = Path(storage_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found at storage path: {storage_path}")

        with open(path, "rb") as f:
            return f.read()


# Default singleton storage instance
default_storage = LocalStorage()


def save_file(file: Union[bytes, BinaryIO], original_filename: str = "") -> str:
    """Convenience function to save a file using the default storage backend."""
    if isinstance(file, bytes):
        content = file
    else:
        content = file.read()
    return default_storage.save_file(content, original_filename)


def get_file(storage_path: str) -> bytes:
    """Convenience function to retrieve a file using the default storage backend."""
    return default_storage.get_file(storage_path)
