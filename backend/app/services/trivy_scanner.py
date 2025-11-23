"""
Trivy scanner integration
"""

import json
from typing import List
from app.services.base_scanner import BaseScanner, ScanResult
from app.core.config import settings
from app.core.logging import logger


class TrivyScanner(BaseScanner):
    """Trivy vulnerability scanner for dependencies and containers"""

    def __init__(self):
        super().__init__("trivy")

    async def scan(self, repo_path: str, **kwargs) -> List[ScanResult]:
        """Run Trivy scan on repository"""
        logger.info(f"Running Trivy scan on {repo_path}")

        # Trivy can scan filesystem for dependencies
        cmd = [
            "trivy",
            "fs",
            "--format", "json",
            "--severity", settings.TRIVY_SEVERITY,
            "--no-progress",
            repo_path
        ]

        # Run Trivy
        result = self.run_command(cmd, cwd=repo_path)

        if not result["success"]:
            logger.error(f"Trivy scan failed: {result['stderr']}")
            return []

        # Parse JSON output
        try:
            output = json.loads(result["stdout"])
            return self._parse_results(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Trivy output: {str(e)}")
            return []

    def _parse_results(self, output: dict) -> List[ScanResult]:
        """Parse Trivy JSON output to ScanResult objects"""
        results = []

        for artifact in output.get("Results", []):
            target = artifact.get("Target", "unknown")

            for vuln in artifact.get("Vulnerabilities", []):
                severity = self.map_severity(vuln.get("Severity", "UNKNOWN"))

                # Get references
                references = []
                if "References" in vuln:
                    references = vuln["References"]
                if "PrimaryURL" in vuln:
                    references.insert(0, vuln["PrimaryURL"])

                result = ScanResult(
                    title=f"{vuln.get('VulnerabilityID', 'Unknown')}: {vuln.get('PkgName', '')}",
                    description=vuln.get("Description", "No description"),
                    severity=severity,
                    type="dependency",
                    scanner="trivy",
                    cve_id=vuln.get("VulnerabilityID"),
                    cwe_id=None,  # Trivy doesn't always provide CWE
                    file_path=target,
                    package_name=vuln.get("PkgName"),
                    package_version=vuln.get("InstalledVersion"),
                    fixed_version=vuln.get("FixedVersion"),
                    cvss_score=self._get_cvss_score(vuln),
                    references=references,
                    remediation=self._get_remediation(vuln),
                    raw_data=vuln
                )

                results.append(result)

        logger.info(f"Trivy found {len(results)} vulnerabilities")
        return results

    def _get_cvss_score(self, vuln: dict) -> float:
        """Extract CVSS score from vulnerability"""
        if "CVSS" in vuln:
            cvss_data = vuln["CVSS"]
            # Try to get the highest CVSS score
            for source, data in cvss_data.items():
                if isinstance(data, dict) and "V3Score" in data:
                    return float(data["V3Score"])
                elif isinstance(data, dict) and "V2Score" in data:
                    return float(data["V2Score"])
        return None

    def _get_remediation(self, vuln: dict) -> str:
        """Generate remediation advice"""
        fixed_version = vuln.get("FixedVersion")
        pkg_name = vuln.get("PkgName")

        if fixed_version and pkg_name:
            return f"Upgrade {pkg_name} to version {fixed_version} or later"

        return "No fix available yet. Monitor the vulnerability for updates."
