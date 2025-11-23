"""
Celery tasks for Ollama AI analysis
"""

from celery import Task
from typing import List, Dict
import asyncio

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.vulnerability import Vulnerability
from app.models.repository import Repository
from app.services.ollama_service import ollama_service
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


@celery_app.task(base=DatabaseTask, bind=True, max_retries=2)
def generate_vulnerability_summaries(self, scan_id: str):
    """
    Generate AI summaries for all vulnerabilities in a scan

    Args:
        scan_id: UUID of the scan
    """
    logger.info(f"Generating AI summaries for scan: {scan_id}")

    # Check if Ollama is available
    if not asyncio.run(ollama_service.check_health()):
        logger.warning("Ollama is not available, skipping AI analysis")
        return {"status": "skipped", "reason": "ollama_unavailable"}

    # Get scan and vulnerabilities
    scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        logger.error(f"Scan not found: {scan_id}")
        return {"status": "error", "message": "Scan not found"}

    vulnerabilities = self.db.query(Vulnerability).filter(
        Vulnerability.scan_id == scan_id
    ).all()

    if not vulnerabilities:
        logger.info(f"No vulnerabilities found for scan: {scan_id}")
        return {"status": "completed", "summaries_generated": 0}

    # Generate summaries for each vulnerability
    summaries_generated = 0
    fixes_generated = 0

    for vuln in vulnerabilities:
        try:
            # Generate summary
            summary = asyncio.run(ollama_service.summarize_vulnerability(
                title=vuln.title,
                description=vuln.description,
                severity=vuln.severity.value,
                cwe_id=vuln.cwe_id,
                file_path=vuln.file_path,
                code_snippet=vuln.code_snippet
            ))

            if summary:
                # Store summary in scan's ai_summary field (we'll use JSON for multiple)
                summaries_generated += 1
                logger.info(f"Generated summary for vulnerability: {vuln.id}")

            # Generate code fix suggestion if code snippet is available
            if vuln.code_snippet and vuln.file_path:
                fix_suggestion = asyncio.run(ollama_service.suggest_fix(
                    title=vuln.title,
                    description=vuln.description,
                    code_snippet=vuln.code_snippet,
                    file_path=vuln.file_path
                ))

                if fix_suggestion:
                    vuln.ai_suggested_fix = fix_suggestion
                    fixes_generated += 1
                    logger.info(f"Generated fix suggestion for vulnerability: {vuln.id}")

            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to generate AI content for vulnerability {vuln.id}: {str(e)}")
            continue

    # Generate overall scan summary
    try:
        repository = self.db.query(Repository).filter(
            Repository.id == scan.repository_id
        ).first()

        if repository:
            vuln_data = [
                {
                    "title": v.title,
                    "severity": v.severity.value,
                    "type": v.type.value
                }
                for v in vulnerabilities[:20]  # Limit to top 20 for context
            ]

            impact_analysis = asyncio.run(ollama_service.analyze_impact(
                vulnerabilities=vuln_data,
                repository_name=repository.full_name
            ))

            if impact_analysis:
                scan.ai_summary = impact_analysis
                scan.ai_analysis_completed = True
                self.db.commit()
                logger.info(f"Generated impact analysis for scan: {scan_id}")

    except Exception as e:
        logger.error(f"Failed to generate scan summary: {str(e)}")

    logger.info(f"AI analysis completed for scan {scan_id}: {summaries_generated} summaries, {fixes_generated} fixes")

    return {
        "status": "completed",
        "summaries_generated": summaries_generated,
        "fixes_generated": fixes_generated
    }


@celery_app.task(base=DatabaseTask, bind=True)
def analyze_vulnerability_trends(self, user_id: str):
    """
    Analyze vulnerability trends for a user using AI

    Args:
        user_id: UUID of the user
    """
    logger.info(f"Analyzing vulnerability trends for user: {user_id}")

    # TODO: Implement trend analysis
    # This would analyze historical vulnerability data and provide insights

    return {"status": "not_implemented"}


@celery_app.task(base=DatabaseTask, bind=True)
def answer_security_query(self, query: str, user_id: str):
    """
    Answer natural language security queries using AI

    Args:
        query: User's question
        user_id: UUID of the user asking the question

    Returns:
        AI-generated answer
    """
    logger.info(f"Processing security query for user {user_id}: {query}")

    # Check if Ollama is available
    if not asyncio.run(ollama_service.check_health()):
        return {"status": "error", "message": "AI service is not available"}

    try:
        # Get recent vulnerabilities for context
        from app.models.user import User

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        # Get user's recent vulnerabilities
        recent_vulns = self.db.query(Vulnerability).join(Scan).join(Repository).filter(
            Repository.owner_id == user_id
        ).order_by(Vulnerability.created_at.desc()).limit(10).all()

        # Build context from recent vulnerabilities
        context = "Recent vulnerabilities in your repositories:\n"
        for vuln in recent_vulns:
            context += f"- [{vuln.severity.value.upper()}] {vuln.title}\n"

        # Get answer from Ollama
        answer = asyncio.run(ollama_service.answer_query(
            query=query,
            context=context
        ))

        if answer:
            return {"status": "success", "answer": answer}
        else:
            return {"status": "error", "message": "Failed to generate answer"}

    except Exception as e:
        logger.error(f"Failed to answer security query: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
