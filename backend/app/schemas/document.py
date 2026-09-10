from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class FileValidationResult(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: str  # "PASS" or "FAIL"
    error_message: Optional[str] = None

class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: Dict[str, Any]
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = None
    status: str  # "PASS", "FAIL", "NOT_APPLICABLE"
    message: Optional[str] = None

class ValidationResult(BaseModel):
    checks: List[ValidationCheck] = Field(default_factory=list)
    overall_status: str  # "PASS", "FAIL", "NOT_APPLICABLE"
    issues: List[str] = Field(default_factory=list)

class ProcessingMetadata(BaseModel):
    ocr_used: bool
    processed_at: str
    processing_time_ms: float
    page_count: int
    extracted_fields_count: int = 0
    engine: str = "PyMuPDF+LLM"

class DocumentProcessResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str  # "PASS", "FAIL", "VALIDATION_FAILED", "REJECTED"
    overall_confidence: Optional[float] = None
    file_validation: FileValidationResult
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    validation: ValidationResult
    processing_metadata: ProcessingMetadata

class DocumentListItem(BaseModel):
    id: int
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    processed_at: str
    page_count: int

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    database_connected: bool
    llm_configured: bool
    ocr_engine_available: bool
    timestamp: str

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
