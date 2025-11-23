"""
Repository model
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class RepositoryProvider(str, enum.Enum):
    """Source code provider"""

    GITHUB = "github"
    GITLAB = "gitlab"


class RepositoryStatus(str, enum.Enum):
    """Repository status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ERROR = "error"


class Repository(Base):
    """Repository model for tracking scanned repositories"""

    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Repository details
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(500), nullable=False)  # e.g., "owner/repo"
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    clone_url = Column(String(500), nullable=False)
    default_branch = Column(String(100), default="main", nullable=False)

    # Provider info
    provider = Column(SQLEnum(RepositoryProvider), nullable=False, index=True)
    provider_id = Column(String(100), nullable=False)  # GitHub/GitLab repo ID
    provider_data = Column(JSON, nullable=True)  # Additional provider-specific data

    # Status
    status = Column(SQLEnum(RepositoryStatus), default=RepositoryStatus.ACTIVE, nullable=False, index=True)
    is_private = Column(Boolean, default=False, nullable=False)
    is_fork = Column(Boolean, default=False, nullable=False)

    # Scan configuration
    auto_scan = Column(Boolean, default=True, nullable=False)
    scan_on_pr = Column(Boolean, default=True, nullable=False)
    scan_schedule = Column(String(100), nullable=True)  # Cron expression

    # Statistics
    total_scans = Column(Integer, default=0, nullable=False)
    last_scan_at = Column(DateTime, nullable=True)
    vulnerabilities_count = Column(Integer, default=0, nullable=False)

    # Language detection
    primary_language = Column(String(50), nullable=True)
    languages = Column(JSON, nullable=True)  # {"Python": 75, "JavaScript": 25}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository {self.full_name}>"
