"""
Scan model
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ScanStatus(str, enum.Enum):
    """Scan execution status"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanTrigger(str, enum.Enum):
    """How the scan was triggered"""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    API = "api"


class Scan(Base):
    """Scan model for tracking security scans"""

    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)

    # Scan details
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING, nullable=False, index=True)
    trigger = Column(SQLEnum(ScanTrigger), default=ScanTrigger.MANUAL, nullable=False)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Git information
    commit_sha = Column(String(40), nullable=True)
    branch = Column(String(255), nullable=True)
    commit_message = Column(Text, nullable=True)

    # Scan configuration
    scanners_used = Column(JSON, nullable=True)  # ["semgrep", "trivy", "gitleaks"]
    scan_config = Column(JSON, nullable=True)  # Scanner-specific configuration

    # Results summary
    total_vulnerabilities = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    medium_count = Column(Integer, default=0, nullable=False)
    low_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)

    # Execution metrics
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Ollama analysis
    ai_summary = Column(Text, nullable=True)
    ai_analysis_completed = Column(Boolean, default=False, nullable=False)

    # Celery task ID
    celery_task_id = Column(String(255), nullable=True, unique=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="scans")
    vulnerabilities = relationship("Vulnerability", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan {self.id} - {self.status}>"
