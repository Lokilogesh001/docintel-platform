import io
import os
from typing import Tuple, Optional
from PIL import Image
import fitz  # PyMuPDF
from backend.app.core.config import settings
from backend.app.schemas.document import FileValidationResult

class DocumentValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class DocumentValidationService:
    @staticmethod
    def detect_mime_from_magic_bytes(content: bytes) -> Optional[str]:
        """Inspects file binary signature (magic bytes) to verify true format."""
        if not content:
            return None
        if content.startswith(b"%PDF-"):
            return "application/pdf"
        if content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\x89PNG"):
            return "image/png"
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        return None

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Tuple[FileValidationResult, Optional[DocumentValidationError]]:
        """
        Validates:
        1. Non-empty file
        2. Maximum file size
        3. Extension & binary magic bytes
        4. PDF integrity & corruption check
        5. Image readability check
        6. Maximum page count <= 3
        """
        # 1. Empty file check
        if not content or len(content) == 0:
            err = DocumentValidationError("EMPTY_FILE", "The uploaded file is empty (0 bytes).")
            return FileValidationResult(
                file_type="unknown",
                is_supported=False,
                is_readable=False,
                page_count=0,
                status="FAIL",
                error_message=err.message
            ), err

        # 2. File size limit
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            err = DocumentValidationError("FILE_TOO_LARGE", f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB.")
            return FileValidationResult(
                file_type="unknown",
                is_supported=False,
                is_readable=False,
                page_count=0,
                status="FAIL",
                error_message=err.message
            ), err

        # 3. Extension check
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.SUPPORTED_EXTENSIONS:
            err = DocumentValidationError(
                "UNSUPPORTED_FILE_TYPE",
                f"File extension '{ext}' is not supported. Only PDF / JPG / PNG documents are supported."
            )
            return FileValidationResult(
                file_type="unknown",
                is_supported=False,
                is_readable=False,
                page_count=0,
                status="FAIL",
                error_message=err.message
            ), err

        # 4. Binary signature verification
        detected_mime = cls.detect_mime_from_magic_bytes(content)
        if not detected_mime or detected_mime not in settings.SUPPORTED_MIME_TYPES:
            err = DocumentValidationError(
                "UNSUPPORTED_FILE_TYPE",
                "Binary file signature does not match supported formats. Only PDF / JPG / PNG documents are supported."
            )
            return FileValidationResult(
                file_type="unknown",
                is_supported=False,
                is_readable=False,
                page_count=0,
                status="FAIL",
                error_message=err.message
            ), err

        # 5. Format-specific deep validation (Corruption & Page Count)
        page_count = 1
        if detected_mime == "application/pdf":
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                if doc.page_count == 0 or doc.is_encrypted:
                    err = DocumentValidationError("CORRUPTED_PDF", "PDF document is corrupt, unreadable or password-protected.")
                    return FileValidationResult(
                        file_type=detected_mime,
                        is_supported=True,
                        is_readable=False,
                        page_count=0,
                        status="FAIL",
                        error_message=err.message
                    ), err

                page_count = doc.page_count
                doc.close()
            except Exception as e:
                err = DocumentValidationError("CORRUPTED_PDF", f"Failed to parse PDF document: {str(e)}")
                return FileValidationResult(
                    file_type=detected_mime,
                    is_supported=True,
                    is_readable=False,
                    page_count=0,
                    status="FAIL",
                    error_message=err.message
                ), err

            # 6. Page limit enforcement
            if page_count > settings.MAX_PAGE_COUNT:
                err = DocumentValidationError(
                    "PAGE_LIMIT_EXCEEDED",
                    f"Document contains {page_count} pages, exceeding the maximum allowed limit of {settings.MAX_PAGE_COUNT} pages."
                )
                return FileValidationResult(
                    file_type=detected_mime,
                    is_supported=True,
                    is_readable=True,
                    page_count=page_count,
                    status="FAIL",
                    error_message=err.message
                ), err

        elif detected_mime in ("image/jpeg", "image/png"):
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
                page_count = 1
            except Exception as e:
                err = DocumentValidationError("CORRUPTED_IMAGE", f"Corrupted or unreadable image file: {str(e)}")
                return FileValidationResult(
                    file_type=detected_mime,
                    is_supported=True,
                    is_readable=False,
                    page_count=0,
                    status="FAIL",
                    error_message=err.message
                ), err

        # Document passed all validation checks
        return FileValidationResult(
            file_type=detected_mime,
            is_supported=True,
            is_readable=True,
            page_count=page_count,
            status="PASS"
        ), None
