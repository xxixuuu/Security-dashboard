"""
Vulnerability management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.vulnerability import Vulnerability, Severity, VulnerabilityStatus, VulnerabilityType
from app.schemas.vulnerability import (
    VulnerabilityUpdate,
    VulnerabilityResponse,
    VulnerabilitySummary,
)
from app.api.auth import get_current_active_user
from app.core.logging import logger

router = APIRouter()


@router.get("/", response_model=List[VulnerabilityResponse])
async def list_vulnerabilities(
    repository_id: str = None,
    scan_id: str = None,
    severity: Severity = None,
    status: VulnerabilityStatus = None,
    vuln_type: VulnerabilityType = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List vulnerabilities for current user"""
    query = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    )

    if repository_id:
        query = query.filter(Scan.repository_id == repository_id)

    if scan_id:
        query = query.filter(Vulnerability.scan_id == scan_id)

    if severity:
        query = query.filter(Vulnerability.severity == severity)

    if status:
        query = query.filter(Vulnerability.status == status)

    if vuln_type:
        query = query.filter(Vulnerability.type == vuln_type)

    vulnerabilities = query.order_by(
        Vulnerability.severity.desc(),
        Vulnerability.created_at.desc()
    ).offset(skip).limit(limit).all()

    return vulnerabilities


@router.get("/{vulnerability_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vulnerability_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get vulnerability by ID"""
    vulnerability = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Vulnerability.id == vulnerability_id,
        Repository.owner_id == current_user.id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found"
        )

    return vulnerability


@router.put("/{vulnerability_id}", response_model=VulnerabilityResponse)
async def update_vulnerability(
    vulnerability_id: str,
    vulnerability_data: VulnerabilityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update vulnerability (e.g., mark as false positive, change status)"""
    vulnerability = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Vulnerability.id == vulnerability_id,
        Repository.owner_id == current_user.id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found"
        )

    # Update fields
    update_data = vulnerability_data.dict(exclude_unset=True)

    # Handle false positive marking
    if "is_false_positive" in update_data and update_data["is_false_positive"]:
        vulnerability.marked_false_positive_by = current_user.id
        vulnerability.marked_false_positive_at = datetime.utcnow()

    # Handle status changes
    if "status" in update_data:
        if update_data["status"] == VulnerabilityStatus.RESOLVED:
            vulnerability.resolved_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(vulnerability, field, value)

    db.commit()
    db.refresh(vulnerability)

    logger.info(f"Vulnerability updated: {vulnerability.id}")

    return vulnerability


@router.post("/{vulnerability_id}/resolve")
async def resolve_vulnerability(
    vulnerability_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark vulnerability as resolved"""
    vulnerability = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Vulnerability.id == vulnerability_id,
        Repository.owner_id == current_user.id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found"
        )

    vulnerability.status = VulnerabilityStatus.RESOLVED
    vulnerability.resolved_at = datetime.utcnow()
    db.commit()

    logger.info(f"Vulnerability resolved: {vulnerability.id}")

    return {"message": "Vulnerability marked as resolved"}


@router.post("/{vulnerability_id}/false-positive")
async def mark_false_positive(
    vulnerability_id: str,
    reason: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark vulnerability as false positive"""
    vulnerability = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Vulnerability.id == vulnerability_id,
        Repository.owner_id == current_user.id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found"
        )

    vulnerability.is_false_positive = True
    vulnerability.false_positive_reason = reason
    vulnerability.marked_false_positive_by = current_user.id
    vulnerability.marked_false_positive_at = datetime.utcnow()
    vulnerability.status = VulnerabilityStatus.FALSE_POSITIVE
    db.commit()

    logger.info(f"Vulnerability marked as false positive: {vulnerability.id}")

    return {"message": "Vulnerability marked as false positive"}


@router.delete("/{vulnerability_id}")
async def delete_vulnerability(
    vulnerability_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete vulnerability"""
    vulnerability = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Vulnerability.id == vulnerability_id,
        Repository.owner_id == current_user.id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found"
        )

    db.delete(vulnerability)
    db.commit()

    logger.info(f"Vulnerability deleted: {vulnerability.id}")

    return {"message": "Vulnerability deleted successfully"}


@router.get("/summary/stats", response_model=VulnerabilitySummary)
async def get_vulnerability_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get vulnerability summary statistics for current user"""
    from sqlalchemy import func

    # Base query for user's vulnerabilities
    base_query = db.query(Vulnerability).join(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    )

    total_vulnerabilities = base_query.count()
    open_vulnerabilities = base_query.filter(
        Vulnerability.status == VulnerabilityStatus.OPEN
    ).count()
    resolved_vulnerabilities = base_query.filter(
        Vulnerability.status == VulnerabilityStatus.RESOLVED
    ).count()
    false_positives = base_query.filter(
        Vulnerability.is_false_positive == True
    ).count()

    # By severity
    by_severity_data = db.query(
        Vulnerability.severity,
        func.count(Vulnerability.id)
    ).join(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    ).group_by(Vulnerability.severity).all()

    by_severity = {severity.value: count for severity, count in by_severity_data}

    # By type
    by_type_data = db.query(
        Vulnerability.type,
        func.count(Vulnerability.id)
    ).join(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    ).group_by(Vulnerability.type).all()

    by_type = {vuln_type.value: count for vuln_type, count in by_type_data}

    # By scanner
    by_scanner_data = db.query(
        Vulnerability.scanner,
        func.count(Vulnerability.id)
    ).join(Scan).join(Repository).filter(
        Repository.owner_id == current_user.id
    ).group_by(Vulnerability.scanner).all()

    by_scanner = {scanner: count for scanner, count in by_scanner_data}

    return VulnerabilitySummary(
        total_vulnerabilities=total_vulnerabilities,
        open_vulnerabilities=open_vulnerabilities,
        resolved_vulnerabilities=resolved_vulnerabilities,
        false_positives=false_positives,
        by_severity=by_severity,
        by_type=by_type,
        by_scanner=by_scanner
    )
