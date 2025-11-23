"""
Celery tasks for security scanning
"""

from celery import Task
from datetime import datetime, timedelta
import tempfile
import shutil
import os
from typing import List, Dict

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.repository import Repository
from app.models.vulnerability import Vulnerability
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


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def run_security_scan(self, scan_id: str):
    """
    Run security scan for a repository

    Args:
        scan_id: UUID of the scan to run
    """
    logger.info(f"Starting security scan: {scan_id}")

    # Get scan from database
    scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        logger.error(f"Scan not found: {scan_id}")
        return {"status": "error", "message": "Scan not found"}

    # Get repository
    repository = self.db.query(Repository).filter(Repository.id == scan.repository_id).first()
    if not repository:
        logger.error(f"Repository not found for scan: {scan_id}")
        scan.status = ScanStatus.FAILED
        scan.error_message = "Repository not found"
        self.db.commit()
        return {"status": "error", "message": "Repository not found"}

    try:
        # Update scan status
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.utcnow()
        scan.celery_task_id = self.request.id
        self.db.commit()

        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp(prefix="secdash_")
        repo_path = os.path.join(temp_dir, repository.name)

        try:
            # Clone repository
            logger.info(f"Cloning repository: {repository.clone_url}")
            clone_result = clone_repository(
                repository.clone_url,
                repo_path,
                branch=scan.branch or repository.default_branch
            )

            if not clone_result["success"]:
                raise Exception(f"Failed to clone repository: {clone_result['error']}")

            # Run scanners
            import asyncio
            vulnerabilities = []
            scanners_to_run = scan.scanners_used or ["semgrep", "trivy", "gitleaks"]

            for scanner_name in scanners_to_run:
                logger.info(f"Running scanner: {scanner_name}")
                scanner_results = asyncio.run(run_scanner(scanner_name, repo_path, repository))
                vulnerabilities.extend(scanner_results)

            # Save vulnerabilities to database
            save_vulnerabilities(self.db, scan.id, vulnerabilities)

            # Update scan with results
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()

            # Count vulnerabilities by severity
            from collections import Counter
            severity_counts = Counter(v["severity"] for v in vulnerabilities)

            scan.total_vulnerabilities = len(vulnerabilities)
            scan.critical_count = severity_counts.get("critical", 0)
            scan.high_count = severity_counts.get("high", 0)
            scan.medium_count = severity_counts.get("medium", 0)
            scan.low_count = severity_counts.get("low", 0)
            scan.info_count = severity_counts.get("info", 0)

            # Update repository stats
            repository.total_scans += 1
            repository.last_scan_at = scan.completed_at
            repository.vulnerabilities_count = scan.total_vulnerabilities

            self.db.commit()

            logger.info(f"Scan completed successfully: {scan_id} - Found {scan.total_vulnerabilities} vulnerabilities")

            return {
                "status": "completed",
                "scan_id": scan_id,
                "total_vulnerabilities": scan.total_vulnerabilities,
            }

        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        logger.error(f"Scan failed: {scan_id} - {str(e)}", exc_info=True)

        scan.status = ScanStatus.FAILED
        scan.completed_at = datetime.utcnow()
        scan.error_message = str(e)
        if scan.started_at:
            scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
        self.db.commit()

        # Retry on failure
        raise self.retry(exc=e, countdown=60)


def clone_repository(clone_url: str, target_path: str, branch: str = "main") -> Dict:
    """Clone a git repository"""
    import subprocess

    try:
        # TODO: Handle authentication for private repositories
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, clone_url, target_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        return {"success": True}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Clone timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_scanner(scanner_name: str, repo_path: str, repository: Repository) -> List[Dict]:
    """Run a specific scanner and return vulnerabilities"""
    from app.services.semgrep_scanner import SemgrepScanner
    from app.services.trivy_scanner import TrivyScanner
    from app.services.gitleaks_scanner import GitleaksScanner

    scanners = {
        "semgrep": SemgrepScanner(),
        "trivy": TrivyScanner(),
        "gitleaks": GitleaksScanner(),
    }

    scanner = scanners.get(scanner_name.lower())
    if not scanner:
        logger.warning(f"Unknown scanner: {scanner_name}")
        return []

    try:
        results = await scanner.scan(repo_path)
        # Convert ScanResult objects to dicts
        return [
            {
                "title": r.title,
                "description": r.description,
                "severity": r.severity,
                "type": r.type,
                "scanner": r.scanner,
                "rule_id": r.rule_id,
                "cwe_id": r.cwe_id,
                "cve_id": r.cve_id,
                "file_path": r.file_path,
                "line_number": r.line_number,
                "code_snippet": r.code_snippet,
                "package_name": r.package_name,
                "package_version": r.package_version,
                "fixed_version": r.fixed_version,
                "cvss_score": r.cvss_score,
                "remediation": r.remediation,
                "raw_data": r.raw_data,
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Scanner {scanner_name} failed: {str(e)}", exc_info=True)
        return []


def save_vulnerabilities(db, scan_id: str, vulnerabilities: List[Dict]):
    """Save vulnerabilities to database"""
    import uuid
    from app.models.vulnerability import Severity, VulnerabilityType, VulnerabilityStatus

    for vuln_data in vulnerabilities:
        vulnerability = Vulnerability(
            id=uuid.uuid4(),
            scan_id=scan_id,
            title=vuln_data.get("title"),
            description=vuln_data.get("description"),
            severity=Severity(vuln_data.get("severity", "info")),
            type=VulnerabilityType(vuln_data.get("type", "sast")),
            status=VulnerabilityStatus.OPEN,
            scanner=vuln_data.get("scanner"),
            rule_id=vuln_data.get("rule_id"),
            cwe_id=vuln_data.get("cwe_id"),
            cve_id=vuln_data.get("cve_id"),
            file_path=vuln_data.get("file_path"),
            line_number=vuln_data.get("line_number"),
            code_snippet=vuln_data.get("code_snippet"),
            package_name=vuln_data.get("package_name"),
            package_version=vuln_data.get("package_version"),
            fixed_version=vuln_data.get("fixed_version"),
            cvss_score=vuln_data.get("cvss_score"),
            remediation=vuln_data.get("remediation"),
            raw_data=vuln_data.get("raw_data"),
        )
        db.add(vulnerability)

    db.commit()


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_scans(self):
    """Cleanup scans older than 90 days"""
    logger.info("Running scan cleanup task")

    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Delete old scans
    deleted_count = self.db.query(Scan).filter(
        Scan.created_at < cutoff_date,
        Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED])
    ).delete()

    self.db.commit()

    logger.info(f"Cleaned up {deleted_count} old scans")

    return {"deleted_scans": deleted_count}
