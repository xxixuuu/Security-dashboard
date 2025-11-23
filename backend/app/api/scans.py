"""
Scan management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus, ScanTrigger
from app.schemas.scan import ScanCreate, ScanResponse, ScanSummary
from app.api.auth import get_current_active_user
from app.core.logging import logger

router = APIRouter()


@router.get("/", response_model=List[ScanResponse])
async def list_scans(
    repository_id: str = None,
    status: ScanStatus = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List scans for current user"""
    query = db.query(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    )

    if repository_id:
        query = query.filter(Scan.repository_id == repository_id)

    if status:
        query = query.filter(Scan.status == status)

    scans = query.order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    return scans


@router.post("/{repository_id}/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    repository_id: str,
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create and trigger a new scan"""
    # Verify repository exists and belongs to user
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # Check for active scans
    active_scan = db.query(Scan).filter(
        Scan.repository_id == repository_id,
        Scan.status.in_([ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING])
    ).first()

    if active_scan:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scan already in progress: {active_scan.id}"
        )

    # Create scan
    scan = Scan(
        id=uuid.uuid4(),
        repository_id=repository_id,
        status=ScanStatus.PENDING,
        trigger=ScanTrigger.MANUAL,
        triggered_by=current_user.id,
        branch=scan_data.branch or repository.default_branch,
        commit_sha=scan_data.commit_sha,
        scanners_used=scan_data.scanners_used or ["semgrep", "trivy", "gitleaks"],
        scan_config=scan_data.scan_config,
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    # TODO: Trigger Celery task to run scan
    logger.info(f"Scan created: {scan.id} for repository {repository.full_name}")

    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get scan by ID"""
    scan = db.query(Scan).join(Repository).filter(
        Scan.id == scan_id,
        Repository.owner_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    return scan


@router.post("/{scan_id}/cancel")
async def cancel_scan(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a running scan"""
    scan = db.query(Scan).join(Repository).filter(
        Scan.id == scan_id,
        Repository.owner_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    if scan.status not in [ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel scan with status: {scan.status}"
        )

    # TODO: Cancel Celery task
    scan.status = ScanStatus.CANCELLED
    scan.completed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Scan cancelled: {scan.id}")

    return {"message": "Scan cancelled successfully"}


@router.delete("/{scan_id}")
async def delete_scan(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete scan and all associated vulnerabilities"""
    scan = db.query(Scan).join(Repository).filter(
        Scan.id == scan_id,
        Repository.owner_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    if scan.status in [ScanStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running scan. Cancel it first."
        )

    db.delete(scan)
    db.commit()

    logger.info(f"Scan deleted: {scan.id}")

    return {"message": "Scan deleted successfully"}


@router.get("/summary/stats", response_model=ScanSummary)
async def get_scan_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get scan summary statistics for current user"""
    from sqlalchemy import func
    from datetime import timedelta

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Base query for user's scans
    base_query = db.query(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    )

    total_scans = base_query.count()
    scans_today = base_query.filter(Scan.created_at >= today_start).count()
    scans_this_week = base_query.filter(Scan.created_at >= week_start).count()
    scans_this_month = base_query.filter(Scan.created_at >= month_start).count()

    active_scans = base_query.filter(
        Scan.status.in_([ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING])
    ).count()

    failed_scans = base_query.filter(Scan.status == ScanStatus.FAILED).count()

    # Calculate average duration
    avg_duration = db.query(func.avg(Scan.duration_seconds)).join(Repository).filter(
        Repository.owner_id == current_user.id,
        Scan.status == ScanStatus.COMPLETED,
        Scan.duration_seconds.isnot(None)
    ).scalar()

    return ScanSummary(
        total_scans=total_scans,
        scans_today=scans_today,
        scans_this_week=scans_this_week,
        scans_this_month=scans_this_month,
        active_scans=active_scans,
        failed_scans=failed_scans,
        average_duration=float(avg_duration) if avg_duration else None
    )
