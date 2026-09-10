import json
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.document import DocumentRecord

class DocumentRepository:
    @staticmethod
    def create_or_append(
        db: Session,
        document_name: str,
        document_type: str,
        processing_status: str,
        file_validation: dict,
        extracted_data: dict,
        validation: dict,
        processing_metadata: dict,
        overall_confidence: Optional[float] = None
    ) -> DocumentRecord:
        record = DocumentRecord(
            document_name=document_name,
            document_type=document_type,
            processing_status=processing_status,
            overall_confidence=overall_confidence,
            file_validation_json=json.dumps(file_validation or {}),
            extracted_data_json=json.dumps(extracted_data or {}),
            validation_json=json.dumps(validation or {}),
            processing_metadata_json=json.dumps(processing_metadata or {})
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_latest_by_name(db: Session, document_name: str) -> Optional[DocumentRecord]:
        return (
            db.query(DocumentRecord)
            .filter(DocumentRecord.document_name == document_name)
            .order_by(DocumentRecord.created_at.desc())
            .first()
        )

    @staticmethod
    def list_documents(db: Session, limit: int = 100, offset: int = 0) -> List[DocumentRecord]:
        return (
            db.query(DocumentRecord)
            .order_by(DocumentRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, doc_id: int) -> Optional[DocumentRecord]:
        return db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
