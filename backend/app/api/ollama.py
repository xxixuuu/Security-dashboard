"""
Ollama AI integration API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.models.user import User
from app.api.auth import get_current_active_user
from app.services.ollama_service import ollama_service
from app.core.logging import logger

router = APIRouter()


class QueryRequest(BaseModel):
    """Schema for AI query request"""
    query: str
    context: Optional[str] = None


class QueryResponse(BaseModel):
    """Schema for AI query response"""
    answer: str
    model_used: str


@router.get("/health")
async def check_ollama_health(
    current_user: User = Depends(get_current_active_user)
):
    """Check if Ollama service is available"""
    is_healthy = await ollama_service.check_health()

    return {
        "available": is_healthy,
        "enabled": ollama_service.enabled,
        "host": ollama_service.base_url
    }


@router.get("/models")
async def list_ollama_models(
    current_user: User = Depends(get_current_active_user)
):
    """List available Ollama models"""
    if not ollama_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is disabled"
        )

    models = await ollama_service.list_models()

    return {
        "models": models,
        "count": len(models)
    }


@router.post("/query", response_model=QueryResponse)
async def query_ai(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Ask a security-related question to the AI

    This endpoint allows users to query the AI about security vulnerabilities,
    best practices, and get explanations about findings.
    """
    if not ollama_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not available"
        )

    # Check health before processing
    if not await ollama_service.check_health():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable"
        )

    answer = await ollama_service.answer_query(
        query=request.query,
        context=request.context
    )

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer"
        )

    logger.info(f"AI query answered for user {current_user.username}: {request.query[:50]}...")

    return QueryResponse(
        answer=answer,
        model_used="llama3.2"
    )


@router.post("/vulnerabilities/{vulnerability_id}/regenerate-summary")
async def regenerate_vulnerability_summary(
    vulnerability_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Regenerate AI summary for a specific vulnerability

    This allows users to refresh the AI analysis if needed.
    """
    if not ollama_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not available"
        )

    # TODO: Fetch vulnerability from database and generate new summary
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Feature coming soon"
    )


@router.post("/scans/{scan_id}/analyze")
async def analyze_scan_with_ai(
    scan_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger AI analysis for a scan

    This endpoint triggers asynchronous AI analysis for all vulnerabilities
    found in a scan.
    """
    if not ollama_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not available"
        )

    # Trigger Celery task
    from app.workers.ollama_tasks import generate_vulnerability_summaries

    task = generate_vulnerability_summaries.delay(scan_id)

    logger.info(f"AI analysis triggered for scan {scan_id} by user {current_user.username}")

    return {
        "message": "AI analysis started",
        "task_id": task.id,
        "scan_id": scan_id
    }
