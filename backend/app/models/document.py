import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from backend.app.core.database import Base

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_name = Column(String(255), index=True, nullable=False)
    document_type = Column(String(50), index=True, nullable=False)
    processing_status = Column(String(50), nullable=False, default="PENDING")
    overall_confidence = Column(Float, nullable=True)

    # Store structured objects as JSON text for cross-database resilience
    file_validation_json = Column(Text, nullable=False, default="{}")
    extracted_data_json = Column(Text, nullable=False, default="{}")
    validation_json = Column(Text, nullable=False, default="{}")
    processing_metadata_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def file_validation(self):
        try:
            return json.loads(self.file_validation_json or "{}")
        except Exception:
            return {}

    @file_validation.setter
    def file_validation(self, val):
        self.file_validation_json = json.dumps(val or {})

    @property
    def extracted_data(self):
        try:
            return json.loads(self.extracted_data_json or "{}")
        except Exception:
            return {}

    @extracted_data.setter
    def extracted_data(self, val):
        self.extracted_data_json = json.dumps(val or {})

    @property
    def validation(self):
        try:
            return json.loads(self.validation_json or "{}")
        except Exception:
            return {}

    @validation.setter
    def validation(self, val):
        self.validation_json = json.dumps(val or {})

    @property
    def processing_metadata(self):
        try:
            return json.loads(self.processing_metadata_json or "{}")
        except Exception:
            return {}

    @processing_metadata.setter
    def processing_metadata(self, val):
        self.processing_metadata_json = json.dumps(val or {})
