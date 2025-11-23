"""
Gitleaks scanner integration for secret detection
"""

import json
from typing import List
from app.services.base_scanner import BaseScanner, ScanResult
from app.core.logging import logger


class GitleaksScanner(BaseScanner):
    """Gitleaks scanner for detecting secrets in code"""

    def __init__(self):
        super().__init__("gitleaks")

    async def scan(self, repo_path: str, **kwargs) -> List[ScanResult]:
        """Run Gitleaks scan on repository"""
        logger.info(f"Running Gitleaks scan on {repo_path}")

        cmd = [
            "gitleaks",
            "detect",
            "--source", repo_path,
            "--report-format", "json",
            "--report-path", "/tmp/gitleaks-report.json",
            "--no-git",  # Don't require .git directory
            "--exit-code", "0",  # Don't exit with error code on findings
        ]

        # Run Gitleaks
        result = self.run_command(cmd, cwd=repo_path)

        # Gitleaks returns exit code 1 when secrets are found, which is expected
        if result["returncode"] not in [0, 1]:
            logger.error(f"Gitleaks scan failed: {result['stderr']}")
            return []

        # Read the report file
        try:
            with open("/tmp/gitleaks-report.json", "r") as f:
                output = json.load(f)
            return self._parse_results(output)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read Gitleaks report: {str(e)}")
            return []

    def _parse_results(self, output: list) -> List[ScanResult]:
        """Parse Gitleaks JSON output to ScanResult objects"""
        results = []

        # Gitleaks output is a list of findings
        if not isinstance(output, list):
            output = [output]

        for finding in output:
            # All secrets are considered high severity by default
            severity = "high"

            # Some secret types might be critical
            secret_type = finding.get("RuleID", "").lower()
            if any(keyword in secret_type for keyword in ["password", "private_key", "api_key", "token"]):
                severity = "critical"

            result = ScanResult(
                title=f"Secret Detected: {finding.get('RuleID', 'Unknown')}",
                description=finding.get("Description", "Potential secret or sensitive information detected"),
                severity=severity,
                type="secret",
                scanner="gitleaks",
                rule_id=finding.get("RuleID"),
                file_path=finding.get("File"),
                line_number=finding.get("StartLine"),
                line_end=finding.get("EndLine"),
                code_snippet=finding.get("Secret", "***REDACTED***"),  # Redact actual secret
                remediation=self._get_remediation(finding),
                raw_data=finding
            )

            results.append(result)

        logger.info(f"Gitleaks found {len(results)} secrets")
        return results

    def _get_remediation(self, finding: dict) -> str:
        """Generate remediation advice for detected secret"""
        secret_type = finding.get("RuleID", "secret")

        remediation = f"A {secret_type} has been detected in your code. "
        remediation += "To remediate:\n"
        remediation += "1. Remove the secret from the code immediately\n"
        remediation += "2. Rotate/revoke the exposed credential\n"
        remediation += "3. Use environment variables or secret management tools (e.g., HashiCorp Vault)\n"
        remediation += "4. Add the file to .gitignore if it contains secrets\n"
        remediation += "5. Review git history and consider rewriting it to remove the secret"

        return remediation
