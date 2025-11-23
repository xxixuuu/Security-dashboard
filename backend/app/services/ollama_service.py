"""
Ollama LLM integration service
"""

import httpx
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import logger


class OllamaService:
    """Service for interacting with Ollama LLM"""

    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.timeout = settings.OLLAMA_TIMEOUT
        self.enabled = settings.OLLAMA_ENABLED

    async def check_health(self) -> bool:
        """Check if Ollama is available"""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {str(e)}")
            return False

    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {str(e)}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Generate text using Ollama

        Args:
            prompt: The prompt to send to the model
            model: Model name (defaults to settings.OLLAMA_MODEL_SUMMARY)
            system_prompt: System prompt for context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None if failed
        """
        if not self.enabled:
            logger.warning("Ollama is disabled")
            return None

        model = model or settings.OLLAMA_MODEL_SUMMARY

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()

        except httpx.TimeoutException:
            logger.error(f"Ollama request timeout for model {model}")
            return None
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}", exc_info=True)
            return None

    async def summarize_vulnerability(
        self,
        title: str,
        description: str,
        severity: str,
        cwe_id: Optional[str] = None,
        file_path: Optional[str] = None,
        code_snippet: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a concise summary of a vulnerability

        Args:
            title: Vulnerability title
            description: Detailed description
            severity: Severity level
            cwe_id: CWE identifier
            file_path: File where vulnerability was found
            code_snippet: Code snippet showing the vulnerability

        Returns:
            AI-generated summary or None
        """
        system_prompt = """You are a security expert analyzing code vulnerabilities.
Provide concise, actionable summaries that help developers understand and fix security issues quickly.
Focus on the impact and remediation."""

        prompt = f"""Analyze this security vulnerability and provide a brief summary (2-3 sentences):

Title: {title}
Severity: {severity.upper()}
{f'CWE: {cwe_id}' if cwe_id else ''}
{f'File: {file_path}' if file_path else ''}

Description:
{description}

{f'Code Snippet:\n```\n{code_snippet}\n```' if code_snippet else ''}

Provide a summary focusing on:
1. What the vulnerability is
2. Why it's dangerous
3. General approach to fix it"""

        return await self.generate(
            prompt=prompt,
            model=settings.OLLAMA_MODEL_SUMMARY,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=500
        )

    async def suggest_fix(
        self,
        title: str,
        description: str,
        code_snippet: str,
        file_path: str,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate code fix suggestions using code-specialized model

        Args:
            title: Vulnerability title
            description: Detailed description
            code_snippet: Vulnerable code
            file_path: File path (to infer language)
            language: Programming language

        Returns:
            Suggested code fix or None
        """
        # Infer language from file extension if not provided
        if not language and file_path:
            ext_map = {
                '.py': 'Python',
                '.js': 'JavaScript',
                '.ts': 'TypeScript',
                '.java': 'Java',
                '.go': 'Go',
                '.rb': 'Ruby',
                '.php': 'PHP',
                '.cs': 'C#',
                '.cpp': 'C++',
                '.c': 'C',
            }
            ext = '.' + file_path.split('.')[-1] if '.' in file_path else ''
            language = ext_map.get(ext, 'code')

        system_prompt = """You are an expert software engineer specializing in security.
Provide specific, secure code fixes. Show only the corrected code with brief explanation.
Follow best practices and security guidelines."""

        prompt = f"""Fix this security vulnerability in {language}:

Vulnerability: {title}
Issue: {description}

Vulnerable Code:
```{language.lower()}
{code_snippet}
```

Provide:
1. The corrected code (complete replacement)
2. Brief explanation of what was changed and why
3. Any additional security considerations"""

        return await self.generate(
            prompt=prompt,
            model=settings.OLLAMA_MODEL_CODE,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for code generation
            max_tokens=1500
        )

    async def analyze_impact(
        self,
        vulnerabilities: List[Dict],
        repository_name: str
    ) -> Optional[str]:
        """
        Analyze the overall impact of vulnerabilities in a repository

        Args:
            vulnerabilities: List of vulnerabilities
            repository_name: Repository name

        Returns:
            Impact analysis or None
        """
        if not vulnerabilities:
            return "No vulnerabilities found. The repository appears to be secure."

        # Prepare vulnerability summary
        vuln_summary = []
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for vuln in vulnerabilities[:10]:  # Limit to top 10 for context
            severity_counts[vuln.get("severity", "low")] += 1
            vuln_summary.append(
                f"- [{vuln.get('severity', 'unknown').upper()}] {vuln.get('title', 'Unknown')}"
            )

        system_prompt = """You are a security architect analyzing application security posture.
Provide strategic insights about overall security risk and prioritization."""

        prompt = f"""Analyze the security impact of vulnerabilities in repository: {repository_name}

Summary:
- Critical: {severity_counts['critical']}
- High: {severity_counts['high']}
- Medium: {severity_counts['medium']}
- Low: {severity_counts['low']}

Top Vulnerabilities:
{chr(10).join(vuln_summary)}

Provide:
1. Overall risk assessment
2. Priority areas for remediation
3. Potential business impact
4. Recommended next steps"""

        return await self.generate(
            prompt=prompt,
            model=settings.OLLAMA_MODEL_ADVANCED,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=800
        )

    async def answer_query(self, query: str, context: Optional[str] = None) -> Optional[str]:
        """
        Answer natural language queries about vulnerabilities

        Args:
            query: User's question
            context: Additional context (vulnerability data, etc.)

        Returns:
            Answer or None
        """
        system_prompt = """You are a security expert assistant helping developers understand
vulnerabilities in their code. Provide clear, actionable answers."""

        full_prompt = f"Question: {query}"
        if context:
            full_prompt = f"Context:\n{context}\n\n{full_prompt}"

        return await self.generate(
            prompt=full_prompt,
            model=settings.OLLAMA_MODEL_SUMMARY,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000
        )


# Global instance
ollama_service = OllamaService()
