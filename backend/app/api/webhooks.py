"""
Webhook handlers for GitHub and GitLab
"""

from fastapi import APIRouter, Request, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.database import SessionLocal
from app.models.repository import Repository, RepositoryProvider
from app.models.scan import Scan, ScanStatus, ScanTrigger
from app.core.logging import logger
from app.services.github_service import github_service
from app.services.gitlab_service import gitlab_service
import uuid

router = APIRouter()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None)
):
    """
    Handle GitHub webhook events

    Supported events:
    - push: Trigger scan on push to default branch
    - pull_request: Trigger scan on PR open/update
    """
    db = next(get_db())

    try:
        # Get request body
        body = await request.body()
        payload = await request.json()

        # Verify webhook signature if secret is configured
        # In production, you should verify the signature
        # github_service.verify_webhook_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET)

        event_type = x_github_event
        logger.info(f"Received GitHub webhook event: {event_type}")

        if event_type == "push":
            # Handle push event
            repo_data = payload.get("repository", {})
            ref = payload.get("ref", "")
            default_branch = repo_data.get("default_branch", "main")

            # Only trigger scan for default branch
            if not ref.endswith(f"/{default_branch}"):
                logger.info(f"Ignoring push to non-default branch: {ref}")
                return {"message": "Ignored: not default branch"}

            # Find repository in database
            repo_id = str(repo_data.get("id"))
            repository = db.query(Repository).filter(
                Repository.provider == RepositoryProvider.GITHUB,
                Repository.provider_id == repo_id
            ).first()

            if not repository:
                logger.warning(f"Repository not found for GitHub ID: {repo_id}")
                return {"message": "Repository not found"}

            if not repository.auto_scan:
                logger.info(f"Auto-scan disabled for repository: {repository.full_name}")
                return {"message": "Auto-scan disabled"}

            # Create and trigger scan
            scan = Scan(
                id=uuid.uuid4(),
                repository_id=repository.id,
                status=ScanStatus.PENDING,
                trigger=ScanTrigger.WEBHOOK,
                branch=default_branch,
                commit_sha=payload.get("after"),
                scanners_used=["semgrep", "trivy", "gitleaks"]
            )
            db.add(scan)
            db.commit()

            # Trigger async scan
            from app.workers.scan_tasks import run_security_scan
            run_security_scan.delay(str(scan.id))

            logger.info(f"Triggered scan for {repository.full_name} (push)")
            return {"message": "Scan triggered", "scan_id": str(scan.id)}

        elif event_type == "pull_request":
            # Handle pull request event
            action = payload.get("action")
            if action not in ["opened", "synchronize", "reopened"]:
                logger.info(f"Ignoring PR action: {action}")
                return {"message": f"Ignored: PR action {action}"}

            repo_data = payload.get("repository", {})
            pr_data = payload.get("pull_request", {})

            # Find repository in database
            repo_id = str(repo_data.get("id"))
            repository = db.query(Repository).filter(
                Repository.provider == RepositoryProvider.GITHUB,
                Repository.provider_id == repo_id
            ).first()

            if not repository:
                logger.warning(f"Repository not found for GitHub ID: {repo_id}")
                return {"message": "Repository not found"}

            if not repository.scan_on_pr:
                logger.info(f"PR scanning disabled for repository: {repository.full_name}")
                return {"message": "PR scanning disabled"}

            # Create and trigger scan for PR
            pr_number = pr_data.get("number")
            head_ref = pr_data.get("head", {}).get("ref")
            head_sha = pr_data.get("head", {}).get("sha")

            scan = Scan(
                id=uuid.uuid4(),
                repository_id=repository.id,
                status=ScanStatus.PENDING,
                trigger=ScanTrigger.PULL_REQUEST,
                branch=head_ref,
                commit_sha=head_sha,
                pr_number=pr_number,
                scanners_used=["semgrep", "trivy", "gitleaks"]
            )
            db.add(scan)
            db.commit()

            # Trigger async scan
            from app.workers.scan_tasks import run_security_scan
            run_security_scan.delay(str(scan.id))

            logger.info(f"Triggered scan for {repository.full_name} PR #{pr_number}")
            return {"message": "Scan triggered", "scan_id": str(scan.id)}

        elif event_type == "ping":
            # Handle ping event (webhook setup verification)
            logger.info("Received GitHub webhook ping")
            return {"message": "pong"}

        else:
            logger.info(f"Unsupported GitHub event: {event_type}")
            return {"message": f"Event {event_type} not supported"}

    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
    finally:
        db.close()


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: Optional[str] = Header(None),
    x_gitlab_token: Optional[str] = Header(None)
):
    """
    Handle GitLab webhook events

    Supported events:
    - Push Hook: Trigger scan on push to default branch
    - Merge Request Hook: Trigger scan on MR open/update
    """
    db = next(get_db())

    try:
        # Get request body
        body = await request.body()
        payload = await request.json()

        # Verify webhook token if configured
        # In production, verify the token
        # gitlab_service.verify_webhook_token(x_gitlab_token, settings.GITLAB_WEBHOOK_TOKEN)

        event_type = x_gitlab_event or payload.get("object_kind")
        logger.info(f"Received GitLab webhook event: {event_type}")

        if event_type == "push":
            # Handle push event
            project_data = payload.get("project", {})
            ref = payload.get("ref", "")
            default_branch = project_data.get("default_branch", "main")

            # Only trigger scan for default branch
            if not ref.endswith(f"/{default_branch}"):
                logger.info(f"Ignoring push to non-default branch: {ref}")
                return {"message": "Ignored: not default branch"}

            # Find repository in database
            project_id = str(project_data.get("id"))
            repository = db.query(Repository).filter(
                Repository.provider == RepositoryProvider.GITLAB,
                Repository.provider_id == project_id
            ).first()

            if not repository:
                logger.warning(f"Repository not found for GitLab project ID: {project_id}")
                return {"message": "Repository not found"}

            if not repository.auto_scan:
                logger.info(f"Auto-scan disabled for repository: {repository.full_name}")
                return {"message": "Auto-scan disabled"}

            # Create and trigger scan
            scan = Scan(
                id=uuid.uuid4(),
                repository_id=repository.id,
                status=ScanStatus.PENDING,
                trigger=ScanTrigger.WEBHOOK,
                branch=default_branch,
                commit_sha=payload.get("after"),
                scanners_used=["semgrep", "trivy", "gitleaks"]
            )
            db.add(scan)
            db.commit()

            # Trigger async scan
            from app.workers.scan_tasks import run_security_scan
            run_security_scan.delay(str(scan.id))

            logger.info(f"Triggered scan for {repository.full_name} (push)")
            return {"message": "Scan triggered", "scan_id": str(scan.id)}

        elif event_type == "merge_request":
            # Handle merge request event
            action = payload.get("object_attributes", {}).get("action")
            if action not in ["open", "update", "reopen"]:
                logger.info(f"Ignoring MR action: {action}")
                return {"message": f"Ignored: MR action {action}"}

            project_data = payload.get("project", {})
            mr_data = payload.get("object_attributes", {})

            # Find repository in database
            project_id = str(project_data.get("id"))
            repository = db.query(Repository).filter(
                Repository.provider == RepositoryProvider.GITLAB,
                Repository.provider_id == project_id
            ).first()

            if not repository:
                logger.warning(f"Repository not found for GitLab project ID: {project_id}")
                return {"message": "Repository not found"}

            if not repository.scan_on_pr:
                logger.info(f"MR scanning disabled for repository: {repository.full_name}")
                return {"message": "MR scanning disabled"}

            # Create and trigger scan for MR
            mr_iid = mr_data.get("iid")
            source_branch = mr_data.get("source_branch")
            last_commit = mr_data.get("last_commit", {})
            commit_sha = last_commit.get("id")

            scan = Scan(
                id=uuid.uuid4(),
                repository_id=repository.id,
                status=ScanStatus.PENDING,
                trigger=ScanTrigger.MERGE_REQUEST,
                branch=source_branch,
                commit_sha=commit_sha,
                pr_number=mr_iid,
                scanners_used=["semgrep", "trivy", "gitleaks"]
            )
            db.add(scan)
            db.commit()

            # Trigger async scan
            from app.workers.scan_tasks import run_security_scan
            run_security_scan.delay(str(scan.id))

            logger.info(f"Triggered scan for {repository.full_name} MR !{mr_iid}")
            return {"message": "Scan triggered", "scan_id": str(scan.id)}

        else:
            logger.info(f"Unsupported GitLab event: {event_type}")
            return {"message": f"Event {event_type} not supported"}

    except Exception as e:
        logger.error(f"Error processing GitLab webhook: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
    finally:
        db.close()
