"""
Notification model
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class NotificationType(str, enum.Enum):
    """Type of notification"""

    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    NEW_VULNERABILITY = "new_vulnerability"
    CRITICAL_VULNERABILITY = "critical_vulnerability"
    VULNERABILITY_RESOLVED = "vulnerability_resolved"
    WEEKLY_SUMMARY = "weekly_summary"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel"""

    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationPriority(str, enum.Enum):
    """Notification priority"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """Notification model for alerts and notifications"""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification details
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False)

    # Content
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional structured data

    # Delivery status
    is_sent = Column(Boolean, default=False, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Related entities
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type} - {self.user_id}>"
