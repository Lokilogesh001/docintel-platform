import io
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import fitz  # PyMuPDF
from PIL import Image
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger

class PageTextResult(BaseModel):
    page_number: int
    text: str
    is_ocr: bool = False
    word_count: int = 0

class DocumentTextResult(BaseModel):
    pages: List[PageTextResult] = Field(default_factory=list)
    combined_text: str = ""
    ocr_used: bool = False
    page_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseOCRProvider:
    """Interface for pluggable OCR providers."""
    def ocr_image(self, image_bytes: bytes, filename: str = "image.png") -> str:
        raise NotImplementedError

class OCRSpaceProvider(BaseOCRProvider):
    """Free tier OCR.space provider."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OCR_SPACE_API_KEY
        self.endpoint = "https://api.ocr.space/parse/image"

    def ocr_image(self, image_bytes: bytes, filename: str = "image.png") -> str:
        try:
            files = {"file": (filename, image_bytes, "image/png")}
            data = {"apikey": self.api_key, "language": "eng", "isTable": "true"}
            with httpx.Client(timeout=15.0) as client:
                res = client.post(self.endpoint, files=files, data=data)
                if res.status_code == 200:
                    json_data = res.json()
                    parsed = json_data.get("ParsedResults", [])
                    if parsed:
                        return parsed[0].get("ParsedText", "").strip()
        except Exception as e:
            logger.warning(f"OCR.Space request failed: {e}")
        return ""

class LocalFallbackOCRProvider(BaseOCRProvider):
    """Fallback when external OCR is offline or unavailable."""
    def ocr_image(self, image_bytes: bytes, filename: str = "image.png") -> str:
        # If Pillow can read metadata or basic structure
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return f"[Scanned Image Document: {img.size[0]}x{img.size[1]} px, format={img.format}]"
        except Exception:
            return ""

class OCRService:
    def __init__(self, provider: Optional[BaseOCRProvider] = None):
        # Default to OCRSpace with Local fallback
        self.provider = provider or OCRSpaceProvider()
        self.fallback_provider = LocalFallbackOCRProvider()

    def extract_document_text(self, content: bytes, filename: str, mime_type: str) -> DocumentTextResult:
        """
        Main extraction strategy:
        1. For PDFs: check page by page if native text exists.
        2. If native text is present (>20 chars), use native text.
        3. If page is scanned/image (<20 chars), render page to image and apply OCR.
        4. For JPG/PNG: apply OCR directly.
        """
        pages: List[PageTextResult] = []
        any_ocr_used = False

        if mime_type == "application/pdf":
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = doc.page_count

            for page_idx in range(page_count):
                page = doc[page_idx]
                page_num = page_idx + 1
                native_text = page.get_text("text").strip()

                if len(native_text) >= 20:
                    # Useful native text exists
                    words = len(native_text.split())
                    pages.append(PageTextResult(
                        page_number=page_num,
                        text=native_text,
                        is_ocr=False,
                        word_count=words
                    ))
                else:
                    # Scanned or image-based PDF page -> Render to pixmap & OCR
                    any_ocr_used = True
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    ocr_text = self._perform_ocr(img_bytes, f"page_{page_num}.png")

                    if not ocr_text:
                        ocr_text = native_text  # Fallback to whatever minimal text was found

                    words = len(ocr_text.split())
                    pages.append(PageTextResult(
                        page_number=page_num,
                        text=ocr_text,
                        is_ocr=True,
                        word_count=words
                    ))
            doc.close()

        elif mime_type in ("image/jpeg", "image/png"):
            any_ocr_used = True
            ocr_text = self._perform_ocr(content, filename)
            words = len(ocr_text.split())
            pages.append(PageTextResult(
                page_number=1,
                text=ocr_text,
                is_ocr=True,
                word_count=words
            ))
            page_count = 1
        else:
            page_count = 0

        # Assemble combined text preserving page boundaries
        combined_parts = []
        for p in pages:
            combined_parts.append(f"--- PAGE {p.page_number} ---\n{p.text}")
        combined_text = "\n\n".join(combined_parts).strip()

        return DocumentTextResult(
            pages=pages,
            combined_text=combined_text,
            ocr_used=any_ocr_used,
            page_count=page_count,
            metadata={"strategy": "hybrid_native_ocr", "pages_processed": len(pages)}
        )

    def _perform_ocr(self, image_bytes: bytes, filename: str) -> str:
        text = self.provider.ocr_image(image_bytes, filename)
        if not text:
            text = self.fallback_provider.ocr_image(image_bytes, filename)
        return text

ocr_service = OCRService()
