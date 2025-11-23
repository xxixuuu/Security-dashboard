"""
Base scanner class for security scanning
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
import subprocess
import json
from app.core.logging import logger


@dataclass
class ScanResult:
    """Scan result data class"""
    title: str
    description: str
    severity: str  # critical, high, medium, low, info
    type: str  # sast, dependency, secret, container, license
    scanner: str
    rule_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    fixed_version: Optional[str] = None
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    references: Optional[List[str]] = None
    remediation: Optional[str] = None
    raw_data: Optional[Dict] = None


class BaseScanner(ABC):
    """Base class for security scanners"""

    def __init__(self, name: str):
        self.name = name
        self.results: List[ScanResult] = []

    @abstractmethod
    async def scan(self, repo_path: str, **kwargs) -> List[ScanResult]:
        """
        Run the scanner on the repository

        Args:
            repo_path: Path to the cloned repository
            **kwargs: Additional scanner-specific arguments

        Returns:
            List of scan results
        """
        pass

    def run_command(self, cmd: List[str], cwd: str = None, timeout: int = 3600) -> Dict:
        """
        Execute a shell command and return the result

        Args:
            cmd: Command and arguments as list
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            Dict with stdout, stderr, and return code
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timeout",
                "returncode": -1
            }
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)} - {str(e)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def map_severity(self, scanner_severity: str) -> str:
        """
        Map scanner-specific severity to standard severity levels

        Args:
            scanner_severity: Scanner's severity label

        Returns:
            Standardized severity: critical, high, medium, low, info
        """
        severity_map = {
            # Semgrep
            "ERROR": "high",
            "WARNING": "medium",
            "INFO": "low",

            # Trivy
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "UNKNOWN": "info",

            # Generic
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "info",
        }

        return severity_map.get(scanner_severity.upper(), "info")
