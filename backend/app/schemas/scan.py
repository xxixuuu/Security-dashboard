"""
Scan schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.models.scan import ScanStatus, ScanTrigger


class ScanBase(BaseModel):
    """Base scan schema"""
    branch: Optional[str] = None
    commit_sha: Optional[str] = None


class ScanCreate(ScanBase):
    """Schema for scan creation"""
    scanners_used: Optional[List[str]] = None  # ["semgrep", "trivy", "gitleaks"]
    scan_config: Optional[Dict] = None


class ScanResponse(ScanBase):
    """Schema for scan response"""
    id: str
    repository_id: str
    status: ScanStatus
    trigger: ScanTrigger
    commit_message: Optional[str] = None
    scanners_used: Optional[List[str]] = None
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_analysis_completed: bool
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanSummary(BaseModel):
    """Schema for scan summary statistics"""
    total_scans: int
    scans_today: int
    scans_this_week: int
    scans_this_month: int
    active_scans: int
    failed_scans: int
    average_duration: Optional[float] = None
