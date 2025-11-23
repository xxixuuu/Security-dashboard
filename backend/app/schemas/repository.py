"""
Repository schemas for request/response validation
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict
from datetime import datetime
from app.models.repository import RepositoryProvider, RepositoryStatus


class RepositoryBase(BaseModel):
    """Base repository schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    auto_scan: bool = True
    scan_on_pr: bool = True
    scan_schedule: Optional[str] = None  # Cron expression


class RepositoryCreate(RepositoryBase):
    """Schema for repository creation"""
    full_name: str = Field(..., min_length=1, max_length=500)
    url: str
    clone_url: str
    provider: RepositoryProvider
    provider_id: str
    default_branch: str = "main"
    is_private: bool = False
    is_fork: bool = False
    primary_language: Optional[str] = None
    languages: Optional[Dict[str, int]] = None
    provider_data: Optional[Dict] = None


class RepositoryUpdate(BaseModel):
    """Schema for repository update"""
    description: Optional[str] = None
    auto_scan: Optional[bool] = None
    scan_on_pr: Optional[bool] = None
    scan_schedule: Optional[str] = None
    status: Optional[RepositoryStatus] = None


class RepositoryResponse(RepositoryBase):
    """Schema for repository response"""
    id: str
    owner_id: str
    full_name: str
    url: str
    clone_url: str
    default_branch: str
    provider: RepositoryProvider
    provider_id: str
    status: RepositoryStatus
    is_private: bool
    is_fork: bool
    total_scans: int
    last_scan_at: Optional[datetime] = None
    vulnerabilities_count: int
    primary_language: Optional[str] = None
    languages: Optional[Dict[str, int]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryImportRequest(BaseModel):
    """Schema for importing repositories from GitHub/GitLab"""
    provider: RepositoryProvider
    repository_names: Optional[list[str]] = None  # If None, import all
    auto_scan: bool = True
