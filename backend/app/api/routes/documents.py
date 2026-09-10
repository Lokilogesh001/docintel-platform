from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import DocumentRecord
from backend.app.schemas.document import (
    DocumentProcessResponse, DocumentListItem, HealthResponse,
    FileValidationResult, ValidationResult, ProcessingMetadata, ErrorResponse
)
from backend.app.services.document_service import document_service
from backend.app.services.document_validation_service import DocumentValidationError
from backend.app.repositories.document_repository import DocumentRepository

router = APIRouter(prefix="/api/v1", tags=["Documents"])

@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """Health check endpoint exposing system readiness without leaking secrets."""
    db_connected = False
    try:
        # Perform quick select
        db.execute(DocumentRecord.__table__.select().limit(1))
        db_connected = True
    except Exception as e:
        logger.error(f"Health DB check error: {e}")

    llm_configured = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        database_connected=db_connected,
        llm_configured=llm_configured,
        ocr_engine_available=True,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@router.post(
    "/documents/process",
    response_model=DocumentProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation or unsupported file error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def process_document(
    file: UploadFile = File(..., description="Document file (PDF, JPG, PNG)"),
    document_type: str = Form(..., description="Type of document: invoice, balance_sheet, profit_and_loss, cash_flow_statement"),
    db: Session = Depends(get_db)
):
    """Processes an uploaded document through the complete extraction and validation pipeline."""
    # 1. Validate document_type
    doc_type_clean = document_type.strip().lower()
    if doc_type_clean not in settings.SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_DOCUMENT_TYPE",
                    "message": f"Document type '{document_type}' is unsupported. Must be one of: {', '.join(settings.SUPPORTED_DOCUMENT_TYPES)}."
                }
            }
        )

    # 2. Read file content safely
    try:
        content = await file.read()
        filename = file.filename or "uploaded_document"
    except Exception as e:
        logger.error(f"Failed to read uploaded stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "FILE_READ_ERROR",
                    "message": "Failed to read uploaded file."
                }
            }
        )

    # 3. Process document through pipeline
    try:
        response = document_service.process_document(
            db=db,
            filename=filename,
            content=content,
            document_type=doc_type_clean
        )
        return response
    except DocumentValidationError as dve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": dve.code,
                    "message": dve.message
                }
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected processing exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_PROCESSING_ERROR",
                    "message": "An internal error occurred during document processing."
                }
            }
        )

@router.get("/documents/{document_name}", response_model=DocumentProcessResponse)
def get_document_by_name(document_name: str, db: Session = Depends(get_db)):
    """Retrieves the latest processed result for a given document name."""
    record = DocumentRepository.get_latest_by_name(db, document_name)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document with name '{document_name}' not found."
                }
            }
        )

    return DocumentProcessResponse(
        document_name=record.document_name,
        document_type=record.document_type,
        processing_status=record.processing_status,
        overall_confidence=record.overall_confidence,
        file_validation=FileValidationResult(**record.file_validation),
        extracted_data=record.extracted_data,
        validation=ValidationResult(**record.validation),
        processing_metadata=ProcessingMetadata(**record.processing_metadata)
    )

@router.get("/documents", response_model=List[DocumentListItem])
def list_documents(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Retrieves list of processed documents for dashboard visualization."""
    records = DocumentRepository.list_documents(db, limit=limit, offset=offset)
    items = []
    for r in records:
        fval = r.file_validation
        page_cnt = fval.get("page_count", 1)
        meta = r.processing_metadata
        proc_time = meta.get("processed_at", r.created_at.isoformat() if r.created_at else "")
        items.append(DocumentListItem(
            id=r.id,
            document_name=r.document_name,
            document_type=r.document_type,
            processing_status=r.processing_status,
            overall_confidence=r.overall_confidence,
            processed_at=proc_time,
            page_count=page_cnt
        ))
    return items
