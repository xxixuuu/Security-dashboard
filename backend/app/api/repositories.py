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
    from app.services.github_service import GitHubService
    from app.services.gitlab_service import GitLabService
    from app.models.repository import RepositoryProvider

    logger.info(f"Import repositories requested by {current_user.username} from {import_request.provider}")

    imported_repos = []

    try:
        if import_request.provider == RepositoryProvider.GITHUB:
            # Use GitHub service with user's token
            # In production, you'd get the user's GitHub token from user settings
            github = GitHubService()

            # Fetch repositories
            github_repos = await github.list_repositories()

            if not github_repos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch repositories from GitHub or no repositories found"
                )

            # Filter repositories if specific names provided
            if import_request.repository_names:
                github_repos = [
                    repo for repo in github_repos
                    if repo["full_name"] in import_request.repository_names
                ]

            # Import each repository
            for gh_repo in github_repos:
                # Check if already exists
                existing = db.query(Repository).filter(
                    Repository.owner_id == current_user.id,
                    Repository.provider_id == str(gh_repo["id"])
                ).first()

                if existing:
                    logger.info(f"Repository {gh_repo['full_name']} already imported")
                    imported_repos.append(existing)
                    continue

                # Create new repository
                repository = Repository(
                    id=uuid.uuid4(),
                    owner_id=current_user.id,
                    name=gh_repo["name"],
                    full_name=gh_repo["full_name"],
                    description=gh_repo.get("description"),
                    url=gh_repo["html_url"],
                    clone_url=gh_repo["clone_url"],
                    provider=RepositoryProvider.GITHUB,
                    provider_id=str(gh_repo["id"]),
                    default_branch=gh_repo.get("default_branch", "main"),
                    is_private=gh_repo.get("private", False),
                    is_fork=gh_repo.get("fork", False),
                    primary_language=gh_repo.get("language"),
                    auto_scan=import_request.auto_scan,
                    provider_data=gh_repo
                )

                db.add(repository)
                imported_repos.append(repository)
                logger.info(f"Imported GitHub repository: {gh_repo['full_name']}")

        elif import_request.provider == RepositoryProvider.GITLAB:
            # Use GitLab service
            gitlab = GitLabService()

            # Fetch projects
            gitlab_projects = await gitlab.list_projects()

            if not gitlab_projects:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch projects from GitLab or no projects found"
                )

            # Filter projects if specific names provided
            if import_request.repository_names:
                gitlab_projects = [
                    proj for proj in gitlab_projects
                    if proj["path_with_namespace"] in import_request.repository_names
                ]

            # Import each project
            for gl_proj in gitlab_projects:
                # Check if already exists
                existing = db.query(Repository).filter(
                    Repository.owner_id == current_user.id,
                    Repository.provider_id == str(gl_proj["id"])
                ).first()

                if existing:
                    logger.info(f"Project {gl_proj['path_with_namespace']} already imported")
                    imported_repos.append(existing)
                    continue

                # Create new repository
                repository = Repository(
                    id=uuid.uuid4(),
                    owner_id=current_user.id,
                    name=gl_proj["name"],
                    full_name=gl_proj["path_with_namespace"],
                    description=gl_proj.get("description"),
                    url=gl_proj["web_url"],
                    clone_url=gl_proj["http_url_to_repo"],
                    provider=RepositoryProvider.GITLAB,
                    provider_id=str(gl_proj["id"]),
                    default_branch=gl_proj.get("default_branch", "main"),
                    is_private=gl_proj.get("visibility") == "private",
                    is_fork=gl_proj.get("forked_from_project") is not None,
                    auto_scan=import_request.auto_scan,
                    provider_data=gl_proj
                )

                db.add(repository)
                imported_repos.append(repository)
                logger.info(f"Imported GitLab project: {gl_proj['path_with_namespace']}")

        db.commit()

        # Refresh all imported repos to get database-generated fields
        for repo in imported_repos:
            db.refresh(repo)

        logger.info(f"Successfully imported {len(imported_repos)} repositories")
        return imported_repos

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import repositories: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import repositories: {str(e)}"
        )


@router.post("/{repository_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync repository metadata from GitHub/GitLab"""
    from app.services.github_service import GitHubService
    from app.services.gitlab_service import GitLabService
    from app.models.repository import RepositoryProvider

    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    logger.info(f"Repository sync requested: {repository.full_name}")

    try:
        if repository.provider == RepositoryProvider.GITHUB:
            # Parse owner and repo from full_name (format: "owner/repo")
            parts = repository.full_name.split("/")
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid repository full_name format"
                )

            owner, repo_name = parts
            github = GitHubService()

            # Fetch latest repository data
            gh_repo = await github.get_repository(owner, repo_name)

            if not gh_repo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch repository from GitHub"
                )

            # Update repository metadata
            repository.description = gh_repo.get("description")
            repository.default_branch = gh_repo.get("default_branch", "main")
            repository.is_private = gh_repo.get("private", False)
            repository.is_fork = gh_repo.get("fork", False)
            repository.primary_language = gh_repo.get("language")
            repository.provider_data = gh_repo

            logger.info(f"Synced GitHub repository: {repository.full_name}")

        elif repository.provider == RepositoryProvider.GITLAB:
            gitlab = GitLabService()

            # Fetch latest project data (use provider_id or full_name)
            project_id = repository.full_name  # GitLab accepts path_with_namespace

            gl_proj = await gitlab.get_project(project_id)

            if not gl_proj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch project from GitLab"
                )

            # Update repository metadata
            repository.name = gl_proj["name"]
            repository.description = gl_proj.get("description")
            repository.default_branch = gl_proj.get("default_branch", "main")
            repository.is_private = gl_proj.get("visibility") == "private"
            repository.is_fork = gl_proj.get("forked_from_project") is not None
            repository.provider_data = gl_proj

            logger.info(f"Synced GitLab project: {repository.full_name}")

        db.commit()
        db.refresh(repository)

        return repository

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync repository: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repository: {str(e)}"
        )
