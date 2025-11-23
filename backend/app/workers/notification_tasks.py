"""
Celery tasks for notifications
"""

from celery import Task
from datetime import datetime, timedelta
from typing import List, Dict

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.logging import logger


class DatabaseTask(Task):
    """Base task with database session management"""

    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True)
def send_scan_notification(self, scan_id: str):
    """Send notification when scan completes"""
    from app.models.scan import Scan, ScanStatus
    from app.models.repository import Repository

    logger.info(f"Sending scan notification for scan: {scan_id}")

    scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        logger.error(f"Scan not found: {scan_id}")
        return

    repository = self.db.query(Repository).filter(Repository.id == scan.repository_id).first()
    if not repository:
        logger.error(f"Repository not found for scan: {scan_id}")
        return

    # Prepare notification message
    if scan.status == ScanStatus.COMPLETED:
        title = f"Scan Completed: {repository.full_name}"
        message = f"Found {scan.total_vulnerabilities} vulnerabilities"

        if scan.critical_count > 0:
            message += f" ({scan.critical_count} critical)"

    elif scan.status == ScanStatus.FAILED:
        title = f"Scan Failed: {repository.full_name}"
        message = f"Error: {scan.error_message}"

    else:
        return  # Don't send notification for other statuses

    # TODO: Send to configured notification channels
    logger.info(f"Notification: {title} - {message}")


@celery_app.task(base=DatabaseTask, bind=True)
def send_weekly_report(self):
    """Send weekly vulnerability report to all users"""
    from app.models.user import User
    from app.models.vulnerability import Vulnerability
    from app.models.scan import Scan
    from app.models.repository import Repository

    logger.info("Generating weekly vulnerability report")

    week_ago = datetime.utcnow() - timedelta(days=7)

    users = self.db.query(User).filter(User.is_active == True).all()

    for user in users:
        # Get user's vulnerabilities from the past week
        new_vulns = self.db.query(Vulnerability).join(Scan).join(Repository).filter(
            Repository.owner_id == user.id,
            Vulnerability.first_detected_at >= week_ago
        ).count()

        # Get user's scans from the past week
        scans_count = self.db.query(Scan).join(Repository).filter(
            Repository.owner_id == user.id,
            Scan.created_at >= week_ago
        ).count()

        # TODO: Send email with weekly summary
        logger.info(f"Weekly report for {user.email}: {new_vulns} new vulnerabilities, {scans_count} scans")

    return {"users_notified": len(users)}
