import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger, StageTimer
from backend.app.schemas.document import (
    DocumentProcessResponse, FileValidationResult,
    ValidationResult, ProcessingMetadata
)
from backend.app.services.document_validation_service import (
    DocumentValidationService, DocumentValidationError
)
from backend.app.services.ocr_service import ocr_service
from backend.app.services.extraction_service import extraction_service
from backend.app.services.financial_validation_service import financial_validation_service
from backend.app.services.evidence_service import evidence_service
from backend.app.repositories.document_repository import DocumentRepository

class DocumentService:
    @classmethod
    def process_document(
        cls,
        db: Session,
        filename: str,
        content: bytes,
        document_type: str
    ) -> DocumentProcessResponse:
        start_time = time.perf_counter()
        logger.info(f"Starting processing for '{filename}' ({document_type})")

        # 1. Document Validation Stage
        with StageTimer("Document Validation", filename) as _:
            file_val_result, val_error = DocumentValidationService.validate_file(filename, content)

        if val_error:
            # Document validation failed early
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            meta = ProcessingMetadata(
                ocr_used=False,
                processed_at=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
                page_count=file_val_result.page_count,
                extracted_fields_count=0,
                engine="ValidationGuard"
            )
            # Persist failure record
            DocumentRepository.create_or_append(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status="REJECTED",
                file_validation=file_val_result.model_dump(),
                extracted_data={},
                validation=ValidationResult(checks=[], overall_status="FAIL", issues=[val_error.message]).model_dump(),
                processing_metadata=meta.model_dump(),
                overall_confidence=None
            )
            raise val_error

        # 2. Text Extraction / OCR Stage
        with StageTimer("Text & OCR Extraction", filename) as _:
            doc_text = ocr_service.extract_document_text(
                content=content,
                filename=filename,
                mime_type=file_val_result.file_type
            )

        # 3. AI / Structured Extraction Stage
        with StageTimer("AI Structured Extraction", filename) as _:
            extracted_data = extraction_service.extract(
                document_type=document_type,
                doc_text=doc_text
            )

        # 4. Deterministic Financial Validation Stage
        with StageTimer("Financial Validation", filename) as _:
            validation_res = financial_validation_service.validate(
                document_type=document_type,
                extracted_data=extracted_data
            )

        # 5. Overall Confidence Calculation
        field_evidence = extracted_data.get("field_evidence") or {}
        confidence_scores = []
        for fe in field_evidence.values():
            if isinstance(fe, dict) and fe.get("confidence") is not None:
                confidence_scores.append(fe["confidence"])
        overall_confidence = round(sum(confidence_scores) / len(confidence_scores), 2) if confidence_scores else None

        # Determine Processing Status
        processing_status = validation_res.overall_status

        # 6. Database Persistence Stage
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        llm_engine_used = getattr(extraction_service, "last_llm_engine", None)
        meta = ProcessingMetadata(
            ocr_used=doc_text.ocr_used,
            processed_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=elapsed_ms,
            page_count=file_val_result.page_count,
            extracted_fields_count=len([k for k, v in extracted_data.items() if v is not None]),
            engine="Gemini/OpenAI+RuleEngine" if llm_engine_used else "NLP+RuleEngine",
            llm_engine=llm_engine_used
        )

        with StageTimer("Database Persistence", filename) as _:
            DocumentRepository.create_or_append(
                db=db,
                document_name=filename,
                document_type=document_type,
                processing_status=processing_status,
                file_validation=file_val_result.model_dump(),
                extracted_data=extracted_data,
                validation=validation_res.model_dump(),
                processing_metadata=meta.model_dump(),
                overall_confidence=overall_confidence
            )

        logger.info(f"Finished processing '{filename}' in {elapsed_ms}ms with status {processing_status}")

        return DocumentProcessResponse(
            document_name=filename,
            document_type=document_type,
            processing_status=processing_status,
            overall_confidence=overall_confidence,
            file_validation=file_val_result,
            extracted_data=extracted_data,
            validation=validation_res,
            processing_metadata=meta
        )

document_service = DocumentService()
