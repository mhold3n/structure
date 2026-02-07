"""
LLM Spec Extractor: Extract structured specifications from natural language.

Provides two execution modes:
1. Local model (placeholder) - For routine extraction tasks
2. OpenRouter API - For complex tasks requiring larger models

Determinism: D2 (frozen parameters, validated outputs)
"""

import os
import json
import hashlib
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

# OpenRouter integration (optional, for complex tasks)
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class ExtractionMode(str, Enum):
    """LLM execution mode."""

    LOCAL = "local"  # Local model (placeholder)
    OPENROUTER = "openrouter"  # OpenRouter API for complex tasks


@dataclass
class ExtractionConfig:
    """Configuration for LLM extraction."""

    mode: ExtractionMode = ExtractionMode.LOCAL
    # Frozen parameters for D2 determinism
    temperature: float = 0.0
    max_tokens: int = 1024
    seed: int = 42
    # OpenRouter settings
    openrouter_model: str = "anthropic/claude-3-haiku"
    openrouter_api_key: Optional[str] = None
    # Validation
    require_json_output: bool = True
    max_retries: int = 2


@dataclass
class ExtractionResult:
    """Result from LLM extraction."""

    success: bool
    spec: Optional[dict] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None
    mode_used: ExtractionMode = ExtractionMode.LOCAL
    # Provenance
    model: str = "local-placeholder"
    input_hash: str = ""
    cached: bool = False


# System prompt for structured extraction
EXTRACTION_PROMPT = """You are a specification extractor. \
Given a natural language task request, extract a structured specification.

Output JSON with these fields:
{
  "domain": "experiment|survey|project|operations|analysis|physics|...",
  "intent": "brief description of what user wants",
  "entities": ["key entities mentioned"],
  "parameters": {"param_name": "value"},
  "constraints": ["any constraints or requirements"],
  "ambiguities": ["unclear aspects that need clarification"],
  "complexity": "low|medium|high"
}

Be precise. If something is unclear, add it to ambiguities.
Respond ONLY with valid JSON."""


class LLMSpecExtractor:
    """
    Extract structured specifications from natural language.

    Determinism level: D2 (reproducible with frozen parameters)
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        # Load API key from environment if not provided
        if self.config.openrouter_api_key is None:
            self.config.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

        # Simple in-memory cache for determinism
        self._cache: dict[str, ExtractionResult] = {}

    def extract(
        self,
        user_input: str,
        force_mode: Optional[ExtractionMode] = None,
    ) -> ExtractionResult:
        """
        Extract structured spec from user input.

        Args:
            user_input: Natural language task description
            force_mode: Override automatic mode selection

        Returns:
            ExtractionResult with structured spec or error
        """
        # Compute input hash for caching/determinism
        input_hash = self._hash_input(user_input)

        # Check cache
        if input_hash in self._cache:
            cached = self._cache[input_hash]
            cached.cached = True
            return cached

        # Determine mode
        mode = force_mode or self._select_mode(user_input)

        # Execute extraction
        if mode == ExtractionMode.LOCAL:
            result = self._extract_local(user_input, input_hash)
        else:
            result = self._extract_openrouter(user_input, input_hash)

        # Cache result
        self._cache[input_hash] = result
        return result

    def _select_mode(self, user_input: str) -> ExtractionMode:
        """
        Select extraction mode based on input complexity.

        Uses heuristics to determine if local model is sufficient
        or if OpenRouter should be used for complex tasks.
        """
        # Complexity heuristics
        word_count = len(user_input.split())
        has_multiple_tasks = any(
            kw in user_input.lower()
            for kw in ["and then", "after that", "followed by", "next", "also"]
        )
        has_technical_jargon = any(
            kw in user_input.lower()
            for kw in [
                "heteroscedasticity",
                "multicollinearity",
                "autocorrelation",
                "bayesian",
                "monte carlo",
            ]
        )

        # Use OpenRouter for complex tasks
        if word_count > 200 or has_multiple_tasks or has_technical_jargon:
            if self._openrouter_available():
                return ExtractionMode.OPENROUTER

        return ExtractionMode.LOCAL

    def _openrouter_available(self) -> bool:
        """Check if OpenRouter is configured and available."""
        return (
            HTTPX_AVAILABLE
            and self.config.openrouter_api_key is not None
            and len(self.config.openrouter_api_key) > 0
        )

    def _extract_local(self, user_input: str, input_hash: str) -> ExtractionResult:
        """
        Local extraction placeholder.

        This is a rule-based fallback. In production, replace with
        local model inference (e.g., llama.cpp, vLLM, or Ollama).
        """
        # Simple rule-based extraction as placeholder
        spec = self._rule_based_extraction(user_input)

        return ExtractionResult(
            success=True,
            spec=spec,
            raw_response=json.dumps(spec),
            mode_used=ExtractionMode.LOCAL,
            model="local-placeholder-v1",
            input_hash=input_hash,
        )

    def _rule_based_extraction(self, user_input: str) -> dict:
        """
        Rule-based extraction fallback.

        Replace this with actual local model inference.
        """
        text_lower = user_input.lower()

        # Detect domain
        domain = "general"
        domain_keywords = {
            "experiment": ["experiment", "hypothesis", "control group", "treatment"],
            "survey": ["survey", "questionnaire", "respondent", "sample size"],
            "project": ["project", "milestone", "deadline", "gantt"],
            "operations": ["workflow", "sop", "process", "throughput"],
            "analysis": ["analyze", "regression", "correlation", "statistics"],
            "physics": ["force", "velocity", "pressure", "energy"],
            "chemistry": ["molecule", "reaction", "compound", "element"],
            "math": ["equation", "solve", "calculate", "integral"],
            "code": ["code", "function", "script", "program"],
        }

        for d, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                domain = d
                break

        # Extract entities (simple noun extraction)
        words = user_input.split()
        entities = [w for w in words if len(w) > 4 and w[0].isupper()][:5]

        # Detect complexity
        word_count = len(words)
        if word_count < 20:
            complexity = "low"
        elif word_count < 50:
            complexity = "medium"
        else:
            complexity = "high"

        # Detect potential ambiguities
        ambiguities = []
        ambiguous_terms = [
            "sample",
            "power",
            "significance",
            "rate",
            "effect",
            "control",
        ]
        for term in ambiguous_terms:
            if term in text_lower:
                ambiguities.append(f"'{term}' may have multiple meanings in this context")

        return {
            "domain": domain,
            "intent": user_input[:100] + ("..." if len(user_input) > 100 else ""),
            "entities": entities,
            "parameters": {},
            "constraints": [],
            "ambiguities": ambiguities,
            "complexity": complexity,
        }

    def _extract_openrouter(self, user_input: str, input_hash: str) -> ExtractionResult:
        """
        Extract spec using OpenRouter API.

        Uses frozen parameters for D2 determinism.
        """
        if not self._openrouter_available():
            return ExtractionResult(
                success=False,
                error="OpenRouter not available (missing httpx or API key)",
                mode_used=ExtractionMode.OPENROUTER,
                input_hash=input_hash,
            )

        try:
            response = self._call_openrouter(user_input)

            # Parse JSON response
            spec = self._parse_json_response(response)
            if spec is None:
                return ExtractionResult(
                    success=False,
                    raw_response=response,
                    error="Failed to parse JSON from response",
                    mode_used=ExtractionMode.OPENROUTER,
                    model=self.config.openrouter_model,
                    input_hash=input_hash,
                )

            return ExtractionResult(
                success=True,
                spec=spec,
                raw_response=response,
                mode_used=ExtractionMode.OPENROUTER,
                model=self.config.openrouter_model,
                input_hash=input_hash,
            )

        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"OpenRouter error: {str(e)}",
                mode_used=ExtractionMode.OPENROUTER,
                model=self.config.openrouter_model,
                input_hash=input_hash,
            )

    def _call_openrouter(self, user_input: str) -> str:
        """Make API call to OpenRouter."""
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/structure-framework",
            "X-Title": "Structure Framework",
        }

        payload = {
            "model": self.config.openrouter_model,
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": user_input},
            ],
            # Frozen parameters for D2 determinism
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "seed": self.config.seed,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """Parse JSON from LLM response."""
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                try:
                    return json.loads(response[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass

        return None

    def _hash_input(self, user_input: str) -> str:
        """Create deterministic hash of input."""
        content = f"{user_input}|{self.config.temperature}|{self.config.seed}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def clear_cache(self):
        """Clear the extraction cache."""
        self._cache.clear()


# Singleton instance for convenience
_default_extractor: Optional[LLMSpecExtractor] = None


def get_extractor(config: Optional[ExtractionConfig] = None) -> LLMSpecExtractor:
    """Get or create the default extractor instance."""
    global _default_extractor
    if _default_extractor is None or config is not None:
        _default_extractor = LLMSpecExtractor(config)
    return _default_extractor


def extract_spec(user_input: str) -> ExtractionResult:
    """Convenience function for quick extraction."""
    return get_extractor().extract(user_input)
