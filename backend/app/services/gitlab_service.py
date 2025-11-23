"""
GitLab API integration service
"""

import httpx
from typing import List, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


class GitLabService:
    """Service for interacting with GitLab API"""

    def __init__(self, access_token: Optional[str] = None, gitlab_url: Optional[str] = None):
        """
        Initialize GitLab service

        Args:
            access_token: User's GitLab personal access token (optional, uses default if not provided)
            gitlab_url: GitLab instance URL (default: gitlab.com)
        """
        self.access_token = access_token or settings.GITLAB_TOKEN
        self.base_url = (gitlab_url or settings.GITLAB_URL or "https://gitlab.com").rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"
        self.headers = {
            "PRIVATE-TOKEN": self.access_token
        } if self.access_token else {}

    async def get_user_info(self) -> Optional[Dict]:
        """
        Get authenticated user information

        Returns:
            User information dict or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/user",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitLab user info: {str(e)}")
            return None

    async def list_projects(
        self,
        membership: bool = True,
        archived: bool = False,
        visibility: Optional[str] = None,
        order_by: str = "last_activity_at",
        sort: str = "desc",
        per_page: int = 100
    ) -> List[Dict]:
        """
        List projects for authenticated user

        Args:
            membership: Limit to projects where user is a member
            archived: Include archived projects
            visibility: Can be 'public', 'internal', or 'private'
            order_by: Return projects ordered by field
            sort: 'asc' or 'desc'
            per_page: Results per page (max 100)

        Returns:
            List of project dicts
        """
        try:
            projects = []
            page = 1

            params = {
                "membership": str(membership).lower(),
                "archived": str(archived).lower(),
                "order_by": order_by,
                "sort": sort,
                "per_page": per_page
            }

            if visibility:
                params["visibility"] = visibility

            async with httpx.AsyncClient() as client:
                while True:
                    params["page"] = page

                    response = await client.get(
                        f"{self.api_url}/projects",
                        headers=self.headers,
                        params=params,
                        timeout=30.0
                    )
                    response.raise_for_status()

                    page_projects = response.json()
                    if not page_projects:
                        break

                    projects.extend(page_projects)

                    # Check if there are more pages from headers
                    next_page = response.headers.get("X-Next-Page")
                    if not next_page:
                        break
                    page = int(next_page)

            logger.info(f"Retrieved {len(projects)} projects from GitLab")
            return projects

        except Exception as e:
            logger.error(f"Failed to list GitLab projects: {str(e)}")
            return []

    async def get_project(self, project_id: str) -> Optional[Dict]:
        """
        Get project information

        Args:
            project_id: Project ID or URL-encoded path (e.g., 'namespace/project')

        Returns:
            Project dict or None if failed
        """
        try:
            # URL encode the project_id if it contains slashes
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects/{encoded_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitLab project {project_id}: {str(e)}")
            return None

    async def get_branches(self, project_id: str) -> List[Dict]:
        """
        Get project branches

        Args:
            project_id: Project ID or URL-encoded path

        Returns:
            List of branch dicts
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects/{encoded_id}/repository/branches",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get branches for {project_id}: {str(e)}")
            return []

    async def get_default_branch(self, project_id: str) -> Optional[str]:
        """
        Get project default branch

        Args:
            project_id: Project ID or URL-encoded path

        Returns:
            Default branch name or None
        """
        project_info = await self.get_project(project_id)
        if project_info:
            return project_info.get("default_branch")
        return None

    async def create_webhook(
        self,
        project_id: str,
        webhook_url: str,
        push_events: bool = True,
        merge_requests_events: bool = True,
        enable_ssl_verification: bool = True,
        token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a webhook for project

        Args:
            project_id: Project ID or URL-encoded path
            webhook_url: URL to send webhook events to
            push_events: Trigger on push events
            merge_requests_events: Trigger on merge request events
            enable_ssl_verification: Enable SSL verification
            token: Optional secret token for validation

        Returns:
            Webhook dict or None if failed
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            payload = {
                "url": webhook_url,
                "push_events": push_events,
                "merge_requests_events": merge_requests_events,
                "enable_ssl_verification": enable_ssl_verification
            }

            if token:
                payload["token"] = token

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/projects/{encoded_id}/hooks",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                webhook = response.json()
                logger.info(f"Created webhook for project {project_id}")
                return webhook

        except Exception as e:
            logger.error(f"Failed to create webhook for {project_id}: {str(e)}")
            return None

    async def delete_webhook(self, project_id: str, hook_id: int) -> bool:
        """
        Delete a webhook

        Args:
            project_id: Project ID or URL-encoded path
            hook_id: Webhook ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_url}/projects/{encoded_id}/hooks/{hook_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                logger.info(f"Deleted webhook {hook_id} for project {project_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete webhook {hook_id}: {str(e)}")
            return False

    async def list_webhooks(self, project_id: str) -> List[Dict]:
        """
        List webhooks for a project

        Args:
            project_id: Project ID or URL-encoded path

        Returns:
            List of webhook dicts
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects/{encoded_id}/hooks",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to list webhooks for {project_id}: {str(e)}")
            return []

    async def get_merge_request(
        self,
        project_id: str,
        mr_iid: int
    ) -> Optional[Dict]:
        """
        Get merge request information

        Args:
            project_id: Project ID or URL-encoded path
            mr_iid: Merge request IID (internal ID)

        Returns:
            Merge request dict or None if failed
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects/{encoded_id}/merge_requests/{mr_iid}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get MR !{mr_iid} for {project_id}: {str(e)}")
            return None

    async def list_merge_requests(
        self,
        project_id: str,
        state: str = "opened",
        per_page: int = 30
    ) -> List[Dict]:
        """
        List merge requests for project

        Args:
            project_id: Project ID or URL-encoded path
            state: Can be 'opened', 'closed', 'merged', or 'all'
            per_page: Results per page

        Returns:
            List of merge request dicts
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/projects/{encoded_id}/merge_requests",
                    headers=self.headers,
                    params={"state": state, "per_page": per_page},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to list MRs for {project_id}: {str(e)}")
            return []

    async def create_commit_status(
        self,
        project_id: str,
        sha: str,
        state: str,
        target_url: Optional[str] = None,
        description: Optional[str] = None,
        name: str = "secdash/security-scan"
    ) -> Optional[Dict]:
        """
        Create a commit status (for MR checks)

        Args:
            project_id: Project ID or URL-encoded path
            sha: Commit SHA
            state: Can be 'pending', 'running', 'success', 'failed', 'canceled'
            target_url: Optional URL to link to
            description: Optional description
            name: Status name/context

        Returns:
            Status dict or None if failed
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            payload = {
                "state": state,
                "name": name
            }

            if target_url:
                payload["target_url"] = target_url
            if description:
                payload["description"] = description

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/projects/{encoded_id}/statuses/{sha}",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to create commit status for {sha}: {str(e)}")
            return None

    async def create_merge_request_note(
        self,
        project_id: str,
        mr_iid: int,
        body: str
    ) -> Optional[Dict]:
        """
        Add a comment to a merge request

        Args:
            project_id: Project ID or URL-encoded path
            mr_iid: Merge request IID
            body: Comment text

        Returns:
            Note dict or None if failed
        """
        try:
            import urllib.parse
            encoded_id = urllib.parse.quote(project_id, safe='')

            payload = {"body": body}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/projects/{encoded_id}/merge_requests/{mr_iid}/notes",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to create MR note: {str(e)}")
            return None

    def verify_webhook_token(self, provided_token: str, expected_token: str) -> bool:
        """
        Verify GitLab webhook token

        Args:
            provided_token: X-Gitlab-Token header value
            expected_token: Expected webhook token

        Returns:
            True if token is valid, False otherwise
        """
        import hmac
        if not provided_token or not expected_token:
            return False

        return hmac.compare_digest(provided_token, expected_token)


# Global instance with default token
gitlab_service = GitLabService()
