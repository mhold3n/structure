"""
Tests for LLM Spec Extractor.

Verifies local extraction, OpenRouter integration, caching, and determinism.
"""

import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from router.llm_extractor import (
    LLMSpecExtractor,
    ExtractionConfig,
    ExtractionMode,
    ExtractionResult,
    extract_spec,
)


class TestLocalExtraction:
    """Test local (placeholder) extraction."""

    def test_simple_extraction(self):
        """Simple input should extract successfully."""
        extractor = LLMSpecExtractor()
        result = extractor.extract("Calculate the sample size for my experiment")

        assert result.success
        assert result.spec is not None
        assert result.mode_used == ExtractionMode.LOCAL
        assert "domain" in result.spec

    def test_domain_detection(self):
        """Domain should be detected from keywords."""
        extractor = LLMSpecExtractor()

        # Experiment domain
        result = extractor.extract("Design an experiment with control group")
        assert result.spec["domain"] == "experiment"

        # Survey domain
        result = extractor.extract("Create a questionnaire for respondents")
        assert result.spec["domain"] == "survey"

        # Analysis domain
        result = extractor.extract("Analyze correlation between variables")
        assert result.spec["domain"] == "analysis"

    def test_complexity_detection(self):
        """Complexity should be detected from input length."""
        extractor = LLMSpecExtractor()

        # Short = low complexity
        result = extractor.extract("Calculate mean")
        assert result.spec["complexity"] == "low"

        # Medium length = medium complexity
        result = extractor.extract(
            "I need to analyze the correlation between multiple variables "
            "in my dataset and create visualizations for the results. "
            "The data includes numeric and categorical columns."
        )
        assert result.spec["complexity"] in ["medium", "high"]

    def test_ambiguity_detection(self):
        """Ambiguous terms should be flagged."""
        extractor = LLMSpecExtractor()
        result = extractor.extract("What is the power of my sample?")

        assert result.success
        assert len(result.spec["ambiguities"]) > 0
        assert any("power" in a or "sample" in a for a in result.spec["ambiguities"])


class TestCaching:
    """Test extraction caching for determinism."""

    def test_cache_hit(self):
        """Same input should return cached result."""
        extractor = LLMSpecExtractor()

        result1 = extractor.extract("Test input")
        result2 = extractor.extract("Test input")

        assert result1.input_hash == result2.input_hash
        assert result2.cached is True

    def test_different_inputs_not_cached(self):
        """Different inputs should not share cache."""
        extractor = LLMSpecExtractor()

        result1 = extractor.extract("First input")
        result2 = extractor.extract("Second input")

        assert result1.input_hash != result2.input_hash

    def test_cache_clear(self):
        """Cache should be clearable."""
        extractor = LLMSpecExtractor()

        result1 = extractor.extract("Test input")
        extractor.clear_cache()
        result2 = extractor.extract("Test input")

        assert result2.cached is False


class TestModeSelection:
    """Test automatic mode selection."""

    def test_short_input_uses_local(self):
        """Short, simple input should use local mode."""
        extractor = LLMSpecExtractor()
        result = extractor.extract("Calculate mean of dataset")

        assert result.mode_used == ExtractionMode.LOCAL

    def test_force_mode(self):
        """Force mode should override auto-selection."""
        extractor = LLMSpecExtractor()
        result = extractor.extract("Simple task", force_mode=ExtractionMode.LOCAL)

        assert result.mode_used == ExtractionMode.LOCAL


class TestDeterminism:
    """Test D2 determinism requirements."""

    def test_frozen_parameters(self):
        """Config should have frozen parameters."""
        config = ExtractionConfig()

        assert config.temperature == 0.0
        assert config.seed == 42

    def test_consistent_hash(self):
        """Same input should produce same hash."""
        extractor = LLMSpecExtractor()

        hash1 = extractor._hash_input("Test input")
        hash2 = extractor._hash_input("Test input")

        assert hash1 == hash2

    def test_different_input_different_hash(self):
        """Different inputs should produce different hashes."""
        extractor = LLMSpecExtractor()

        hash1 = extractor._hash_input("Input A")
        hash2 = extractor._hash_input("Input B")

        assert hash1 != hash2


class TestOpenRouterIntegration:
    """Test OpenRouter integration (without actual API calls)."""

    def test_openrouter_not_available_without_key(self):
        """OpenRouter should not be available without API key."""
        # Clear any existing key
        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            config = ExtractionConfig(openrouter_api_key=None)
            extractor = LLMSpecExtractor(config)

            assert extractor._openrouter_available() is False
        finally:
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key

    def test_openrouter_available_with_key(self):
        """OpenRouter should be available with API key (if httpx installed)."""
        config = ExtractionConfig(openrouter_api_key="test-key")
        extractor = LLMSpecExtractor(config)

        # Will be True only if httpx is installed
        from router.llm_extractor import HTTPX_AVAILABLE

        assert extractor._openrouter_available() == HTTPX_AVAILABLE


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_extract_spec_function(self):
        """extract_spec should work as standalone function."""
        result = extract_spec("Simple task")

        assert isinstance(result, ExtractionResult)
        assert result.success


def run_tests():
    """Run all LLM extractor tests."""
    import traceback

    test_classes = [
        TestLocalExtraction,
        TestCaching,
        TestModeSelection,
        TestDeterminism,
        TestOpenRouterIntegration,
        TestConvenienceFunctions,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_class.__name__}")
        print("=" * 60)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
