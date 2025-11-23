"""
Repository management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryStatus
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryImportRequest,
)
from app.api.auth import get_current_active_user
from app.core.logging import logger

router = APIRouter()


@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: RepositoryStatus = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all repositories for current user"""
    query = db.query(Repository).filter(Repository.owner_id == current_user.id)

    if status:
        query = query.filter(Repository.status == status)

    repositories = query.offset(skip).limit(limit).all()
    return repositories


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repository_data: RepositoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new repository"""
    # Check if repository already exists for this user
    existing_repo = db.query(Repository).filter(
        Repository.owner_id == current_user.id,
        Repository.full_name == repository_data.full_name
    ).first()

    if existing_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository {repository_data.full_name} already exists"
        )

    # Create repository
    repository = Repository(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        **repository_data.dict()
    )

    db.add(repository)
    db.commit()
    db.refresh(repository)

    logger.info(f"Repository created: {repository.full_name} by {current_user.username}")

    return repository


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get repository by ID"""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    return repository


@router.put("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: str,
    repository_data: RepositoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update repository settings"""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # Update fields
    update_data = repository_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repository, field, value)

    db.commit()
    db.refresh(repository)

    logger.info(f"Repository updated: {repository.full_name}")

    return repository


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete repository"""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    db.delete(repository)
    db.commit()

    logger.info(f"Repository deleted: {repository.full_name}")

    return {"message": "Repository deleted successfully"}


@router.post("/import", response_model=List[RepositoryResponse])
async def import_repositories(
    import_request: RepositoryImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Import repositories from GitHub/GitLab"""
    # TODO: Implement GitHub/GitLab API integration
    # For now, return empty list
    logger.info(f"Import repositories requested by {current_user.username}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Repository import feature coming soon"
    )


@router.post("/{repository_id}/sync")
async def sync_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync repository metadata from GitHub/GitLab"""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # TODO: Implement sync logic with GitHub/GitLab API
    logger.info(f"Repository sync requested: {repository.full_name}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Repository sync feature coming soon"
    )
