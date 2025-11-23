"""
Semgrep scanner integration
"""

import json
from typing import List
from app.services.base_scanner import BaseScanner, ScanResult
from app.core.config import settings
from app.core.logging import logger


class SemgrepScanner(BaseScanner):
    """Semgrep SAST scanner"""

    def __init__(self):
        super().__init__("semgrep")

    async def scan(self, repo_path: str, **kwargs) -> List[ScanResult]:
        """Run Semgrep scan on repository"""
        logger.info(f"Running Semgrep scan on {repo_path}")

        # Prepare Semgrep command
        config = kwargs.get("config", settings.SEMGREP_RULES)

        cmd = [
            "semgrep",
            "--config", config,
            "--json",
            "--no-git-ignore",
            "--timeout", "300",
            repo_path
        ]

        # Run Semgrep
        result = self.run_command(cmd, cwd=repo_path)

        if not result["success"]:
            logger.error(f"Semgrep scan failed: {result['stderr']}")
            return []

        # Parse JSON output
        try:
            output = json.loads(result["stdout"])
            return self._parse_results(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep output: {str(e)}")
            return []

    def _parse_results(self, output: dict) -> List[ScanResult]:
        """Parse Semgrep JSON output to ScanResult objects"""
        results = []

        for finding in output.get("results", []):
            # Extract vulnerability details
            severity = self.map_severity(finding.get("extra", {}).get("severity", "INFO"))

            # Get CWE from metadata
            metadata = finding.get("extra", {}).get("metadata", {})
            cwe_ids = metadata.get("cwe", [])
            cwe_id = f"CWE-{cwe_ids[0]}" if cwe_ids else None

            # Get code snippet
            code_snippet = None
            if "extra" in finding and "lines" in finding["extra"]:
                code_snippet = finding["extra"]["lines"]

            result = ScanResult(
                title=finding.get("check_id", "Unknown"),
                description=finding.get("extra", {}).get("message", "No description"),
                severity=severity,
                type="sast",
                scanner="semgrep",
                rule_id=finding.get("check_id"),
                cwe_id=cwe_id,
                file_path=finding.get("path"),
                line_number=finding.get("start", {}).get("line"),
                line_end=finding.get("end", {}).get("line"),
                code_snippet=code_snippet,
                references=metadata.get("references", []),
                remediation=metadata.get("fix", {}).get("message"),
                raw_data=finding
            )

            results.append(result)

        logger.info(f"Semgrep found {len(results)} issues")
        return results
