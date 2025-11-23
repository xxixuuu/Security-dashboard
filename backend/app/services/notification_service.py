"""
Notification service for sending alerts via multiple channels
"""

import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from app.core.config import settings
from app.core.logging import logger


class NotificationService:
    """Service for sending notifications via various channels"""

    @staticmethod
    async def send_slack_notification(
        message: str,
        title: Optional[str] = None,
        color: str = "#36a64f",
        fields: Optional[list] = None
    ) -> bool:
        """
        Send notification to Slack via webhook

        Args:
            message: Main message text
            title: Optional title
            color: Color for the attachment (hex)
            fields: Optional list of fields

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.SLACK_ENABLED or not settings.SLACK_WEBHOOK_URL:
            logger.debug("Slack notifications are disabled")
            return False

        try:
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": title or "SecDash Notification",
                        "text": message,
                        "fields": fields or [],
                        "footer": "SecDash Security Dashboard",
                        "ts": int(__import__('time').time())
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info("Slack notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False

    @staticmethod
    async def send_discord_notification(
        message: str,
        title: Optional[str] = None,
        color: int = 0x00ff00,
        fields: Optional[list] = None
    ) -> bool:
        """
        Send notification to Discord via webhook

        Args:
            message: Main message text
            title: Optional title
            color: Color for the embed (decimal)
            fields: Optional list of fields

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.DISCORD_ENABLED or not settings.DISCORD_WEBHOOK_URL:
            logger.debug("Discord notifications are disabled")
            return False

        try:
            embed = {
                "title": title or "SecDash Notification",
                "description": message,
                "color": color,
                "fields": fields or [],
                "footer": {
                    "text": "SecDash Security Dashboard"
                },
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }

            payload = {
                "embeds": [embed]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.DISCORD_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info("Discord notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}")
            return False

    @staticmethod
    async def send_email_notification(
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send email notification via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.EMAIL_ENABLED or not settings.SMTP_HOST:
            logger.debug("Email notifications are disabled")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Add plain text part
            text_part = MIMEText(body, "plain")
            message.attach(text_part)

            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
                timeout=30.0
            )

            logger.info(f"Email notification sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

    @staticmethod
    def get_severity_color_slack(severity: str) -> str:
        """Get Slack color for severity level"""
        colors = {
            "critical": "#d9534f",  # Red
            "high": "#f0ad4e",      # Orange
            "medium": "#f0e68c",    # Yellow
            "low": "#5bc0de",       # Blue
            "info": "#5cb85c",      # Green
        }
        return colors.get(severity.lower(), "#808080")

    @staticmethod
    def get_severity_color_discord(severity: str) -> int:
        """Get Discord color for severity level (decimal)"""
        colors = {
            "critical": 0xff0000,  # Red
            "high": 0xff6600,      # Orange
            "medium": 0xffcc00,    # Yellow
            "low": 0x00ccff,       # Blue
            "info": 0x00ff00,      # Green
        }
        return colors.get(severity.lower(), 0x808080)

    async def notify_scan_completed(
        self,
        repository_name: str,
        scan_id: str,
        total_vulnerabilities: int,
        critical_count: int,
        high_count: int,
        medium_count: int,
        user_email: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send scan completion notification via all enabled channels

        Returns:
            Dict with results for each channel
        """
        # Determine severity color based on findings
        if critical_count > 0:
            severity = "critical"
        elif high_count > 0:
            severity = "high"
        elif total_vulnerabilities > 0:
            severity = "medium"
        else:
            severity = "info"

        # Prepare message
        title = f"Scan Completed: {repository_name}"
        message = f"Security scan found {total_vulnerabilities} vulnerabilities"

        fields = [
            {"title": "Critical", "value": str(critical_count), "inline": True},
            {"title": "High", "value": str(high_count), "inline": True},
            {"title": "Medium", "value": str(medium_count), "inline": True},
        ]

        # Discord fields format
        discord_fields = [
            {"name": f["title"], "value": f["value"], "inline": f.get("inline", False)}
            for f in fields
        ]

        results = {}

        # Send to Slack
        results["slack"] = await self.send_slack_notification(
            message=message,
            title=title,
            color=self.get_severity_color_slack(severity),
            fields=fields
        )

        # Send to Discord
        results["discord"] = await self.send_discord_notification(
            message=message,
            title=title,
            color=self.get_severity_color_discord(severity),
            fields=discord_fields
        )

        # Send email if user email provided
        if user_email:
            email_body = f"""
{title}

Summary:
{message}

Details:
- Critical: {critical_count}
- High: {high_count}
- Medium: {medium_count}

View full report: {settings.FRONTEND_URL}/scans/{scan_id}

---
SecDash Security Dashboard
            """.strip()

            results["email"] = await self.send_email_notification(
                to_email=user_email,
                subject=title,
                body=email_body
            )

        return results

    async def notify_critical_vulnerability(
        self,
        repository_name: str,
        vulnerability_title: str,
        file_path: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send urgent notification for critical vulnerability

        Returns:
            Dict with results for each channel
        """
        title = f"🚨 Critical Vulnerability Detected: {repository_name}"
        message = f"**{vulnerability_title}**"

        if file_path:
            message += f"\n\nFile: `{file_path}`"

        message += "\n\n⚠️ Immediate action required!"

        fields = [
            {"title": "Severity", "value": "CRITICAL", "inline": True},
            {"title": "Repository", "value": repository_name, "inline": True},
        ]

        # Discord fields format
        discord_fields = [
            {"name": f["title"], "value": f["value"], "inline": f.get("inline", False)}
            for f in fields
        ]

        results = {}

        # Send to Slack
        results["slack"] = await self.send_slack_notification(
            message=message,
            title=title,
            color=self.get_severity_color_slack("critical"),
            fields=fields
        )

        # Send to Discord
        results["discord"] = await self.send_discord_notification(
            message=message,
            title=title,
            color=self.get_severity_color_discord("critical"),
            fields=discord_fields
        )

        # Send email
        if user_email:
            email_body = f"""
{title}

{vulnerability_title}

Location: {file_path or 'Unknown'}

This is a CRITICAL severity vulnerability that requires immediate attention.

Please review and address this security issue as soon as possible.

---
SecDash Security Dashboard
            """.strip()

            results["email"] = await self.send_email_notification(
                to_email=user_email,
                subject=title,
                body=email_body
            )

        return results


# Global instance
notification_service = NotificationService()
