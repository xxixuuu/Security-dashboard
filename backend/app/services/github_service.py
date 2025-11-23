"""
GitHub API integration service
"""

import httpx
from typing import List, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize GitHub service

        Args:
            access_token: User's GitHub personal access token (optional, uses default if not provided)
        """
        self.access_token = access_token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.access_token}" if self.access_token else None
        }

    async def get_user_info(self) -> Optional[Dict]:
        """
        Get authenticated user information

        Returns:
            User information dict or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitHub user info: {str(e)}")
            return None

    async def list_repositories(
        self,
        visibility: str = "all",
        affiliation: str = "owner,collaborator,organization_member",
        sort: str = "updated",
        per_page: int = 100
    ) -> List[Dict]:
        """
        List repositories for authenticated user

        Args:
            visibility: Can be 'all', 'public', or 'private'
            affiliation: Comma-separated list of values
            sort: Can be 'created', 'updated', 'pushed', 'full_name'
            per_page: Results per page (max 100)

        Returns:
            List of repository dicts
        """
        try:
            repositories = []
            page = 1

            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        f"{self.base_url}/user/repos",
                        headers=self.headers,
                        params={
                            "visibility": visibility,
                            "affiliation": affiliation,
                            "sort": sort,
                            "per_page": per_page,
                            "page": page
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()

                    repos = response.json()
                    if not repos:
                        break

                    repositories.extend(repos)

                    # Check if there are more pages
                    if len(repos) < per_page:
                        break
                    page += 1

            logger.info(f"Retrieved {len(repositories)} repositories from GitHub")
            return repositories

        except Exception as e:
            logger.error(f"Failed to list GitHub repositories: {str(e)}")
            return []

    async def get_repository(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Get repository information

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository dict or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitHub repository {owner}/{repo}: {str(e)}")
            return None

    async def get_branches(self, owner: str, repo: str) -> List[Dict]:
        """
        Get repository branches

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            List of branch dicts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/branches",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get branches for {owner}/{repo}: {str(e)}")
            return []

    async def get_default_branch(self, owner: str, repo: str) -> Optional[str]:
        """
        Get repository default branch

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Default branch name or None
        """
        repo_info = await self.get_repository(owner, repo)
        if repo_info:
            return repo_info.get("default_branch")
        return None

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        events: List[str] = None,
        secret: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a webhook for repository

        Args:
            owner: Repository owner username
            repo: Repository name
            webhook_url: URL to send webhook events to
            events: List of events to subscribe to (default: ['push', 'pull_request'])
            secret: Optional webhook secret for validation

        Returns:
            Webhook dict or None if failed
        """
        if events is None:
            events = ["push", "pull_request"]

        try:
            payload = {
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                },
                "events": events,
                "active": True
            }

            if secret:
                payload["config"]["secret"] = secret

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                webhook = response.json()
                logger.info(f"Created webhook for {owner}/{repo}")
                return webhook

        except Exception as e:
            logger.error(f"Failed to create webhook for {owner}/{repo}: {str(e)}")
            return None

    async def delete_webhook(self, owner: str, repo: str, hook_id: int) -> bool:
        """
        Delete a webhook

        Args:
            owner: Repository owner username
            repo: Repository name
            hook_id: Webhook ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks/{hook_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                logger.info(f"Deleted webhook {hook_id} for {owner}/{repo}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete webhook {hook_id}: {str(e)}")
            return False

    async def list_webhooks(self, owner: str, repo: str) -> List[Dict]:
        """
        List webhooks for a repository

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            List of webhook dicts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/hooks",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to list webhooks for {owner}/{repo}: {str(e)}")
            return []

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Optional[Dict]:
        """
        Get pull request information

        Args:
            owner: Repository owner username
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Pull request dict or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get PR #{pr_number} for {owner}/{repo}: {str(e)}")
            return None

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30
    ) -> List[Dict]:
        """
        List pull requests for repository

        Args:
            owner: Repository owner username
            repo: Repository name
            state: Can be 'open', 'closed', or 'all'
            per_page: Results per page

        Returns:
            List of pull request dicts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls",
                    headers=self.headers,
                    params={"state": state, "per_page": per_page},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to list PRs for {owner}/{repo}: {str(e)}")
            return []

    async def create_commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        target_url: Optional[str] = None,
        description: Optional[str] = None,
        context: str = "secdash/security-scan"
    ) -> Optional[Dict]:
        """
        Create a commit status (for PR checks)

        Args:
            owner: Repository owner username
            repo: Repository name
            sha: Commit SHA
            state: Can be 'error', 'failure', 'pending', 'success'
            target_url: Optional URL to link to
            description: Optional short description
            context: Status context identifier

        Returns:
            Status dict or None if failed
        """
        try:
            payload = {
                "state": state,
                "context": context
            }

            if target_url:
                payload["target_url"] = target_url
            if description:
                payload["description"] = description

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/statuses/{sha}",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to create commit status for {sha}: {str(e)}")
            return None

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify GitHub webhook signature

        Args:
            payload: Request body bytes
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret

        Returns:
            True if signature is valid, False otherwise
        """
        import hmac
        import hashlib

        if not signature or not secret:
            return False

        # GitHub sends signature as 'sha256=<hash>'
        expected_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)


# Global instance with default token
github_service = GitHubService()
