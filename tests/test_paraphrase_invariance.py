"""
Paraphrase Invariance Tests.

Tests that many different phrasings of the same question produce
the same TaskSpec or the same CLARIFY decision.

This is the core invariance test for "maximum prompt variation,
minimum answer variance."
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.task_spec import TaskRequest, Domain
from models.gate_decision import Decision
from router.classifier import classify_task
from validator.gates import run_gates, get_blocking_decisions


# --- Paraphrase Sets ---

# All of these should trigger CLARIFY for "specific weight" ambiguity
SPECIFIC_WEIGHT_PARAPHRASES = [
    "What is the specific weight of water?",
    "what's the specific weight of water",
    "specific weight of water?",
    "Tell me the specific weight of water",
    "Calculate the specific weight of water",
    "Find the specific weight of water",
    "What is water's specific weight?",
    "I need the specific weight of water",
    "Can you give me the specific weight of water?",
    "What's the specific weight for water?",
    "Specific weight of H2O?",
    "Give me specific weight of water",
    "What is the specific weight of pure water?",
    "What is the specific weight of fresh water?",
    "specific weight water",
    "water specific weight",
    "What would be the specific weight of water?",
    "Please calculate the specific weight of water",
    "Looking for the specific weight of water",
    "Need to know specific weight of water",
    "What's water's specific weight value?",
]

# All of these should trigger CLARIFY for "lb" unit ambiguity
LB_PARAPHRASES = [
    "Convert 10 lb to kg",
    "How many kg in 10 lb?",
    "10 lb in kilograms",
    "What is 10 lb in kg?",
    "10 pounds to kg",
    "10 lb = ? kg",
    "I have 10 lb, how much is that in kg?",
]

# All of these should ACCEPT (no ambiguity)
UNAMBIGUOUS_PARAPHRASES = [
    "What is 2 + 2?",
    "Calculate 2 plus 2",
    "2+2=?",
    "What does 2 + 2 equal?",
    "What is the value of standard gravity?",
    "What is the acceleration due to gravity?",
    "What is pi?",
    "Calculate the area of a circle with radius 5 meters",
    "Area of circle, r = 5m",
    "What is the circumference of a circle with diameter 10 m?",
]

# All of these should route to physics.fluids
FLUIDS_PARAPHRASES = [
    "Calculate the hydrostatic pressure at 10m depth",
    "What is the pressure at 10 meters underwater?",
    "Pressure at depth of 10m in water",
    "Find hydrostatic pressure, depth = 10m",
    "What's the water pressure 10 meters down?",
]


class TestSpecificWeightParaphrase:
    """All phrasings of 'specific weight of water' should CLARIFY."""

    def test_all_paraphrases_clarify(self):
        """Every phrasing should trigger CLARIFY."""
        for i, phrase in enumerate(SPECIFIC_WEIGHT_PARAPHRASES):
            request = TaskRequest(request_id=f"sw-{i}", user_input=phrase)
            spec = classify_task(request)
            gate_results = run_gates(spec)
            blocking = get_blocking_decisions(gate_results)

            assert len(blocking) > 0, f"Phrase should CLARIFY: '{phrase}'"
            assert blocking[0].decision in (
                Decision.CLARIFY,
                Decision.REJECT,
            ), f"Phrase should block: '{phrase}'"

    def test_all_route_to_physics(self):
        """All phrasings should route to physics domain."""
        for i, phrase in enumerate(SPECIFIC_WEIGHT_PARAPHRASES):
            request = TaskRequest(request_id=f"sw-route-{i}", user_input=phrase)
            spec = classify_task(request)

            assert spec.domain == Domain.PHYSICS, f"Should route to physics: '{phrase}'"

    def test_all_include_ambiguity_gate(self):
        """All phrasings should require ambiguity gate."""
        for i, phrase in enumerate(SPECIFIC_WEIGHT_PARAPHRASES):
            request = TaskRequest(request_id=f"sw-gate-{i}", user_input=phrase)
            spec = classify_task(request)

            assert "ambiguity_gate" in spec.required_gates, (
                f"Should need ambiguity gate: '{phrase}'"
            )


class TestLbParaphrase:
    """All phrasings with 'lb' should CLARIFY for unit ambiguity."""

    def test_all_paraphrases_clarify(self):
        """Every phrasing should trigger CLARIFY."""
        for i, phrase in enumerate(LB_PARAPHRASES):
            request = TaskRequest(request_id=f"lb-{i}", user_input=phrase)
            spec = classify_task(request)
            gate_results = run_gates(spec)
            blocking = get_blocking_decisions(gate_results)

            assert len(blocking) > 0, f"Phrase should CLARIFY: '{phrase}'"


class TestUnambiguousParaphrase:
    """Unambiguous requests should all ACCEPT."""

    def test_all_paraphrases_accept(self):
        """Every phrasing should pass gates."""
        for i, phrase in enumerate(UNAMBIGUOUS_PARAPHRASES):
            request = TaskRequest(request_id=f"clear-{i}", user_input=phrase)
            spec = classify_task(request)
            gate_results = run_gates(spec)
            blocking = get_blocking_decisions(gate_results)

            assert len(blocking) == 0, f"Phrase should NOT block: '{phrase}' - got {blocking}"


class TestFluidsParaphrase:
    """Fluids-related requests should all route to physics.fluids."""

    def test_all_route_to_fluids(self):
        """Every phrasing should route to fluids subdomain."""
        for i, phrase in enumerate(FLUIDS_PARAPHRASES):
            request = TaskRequest(request_id=f"fluids-{i}", user_input=phrase)
            spec = classify_task(request)

            assert spec.domain == Domain.PHYSICS, f"Should route to physics: '{phrase}'"
            assert spec.subdomain == "fluids", f"Should route to fluids: '{phrase}'"


class TestParaphraseConsistency:
    """Test that paraphrases produce consistent specs."""

    def test_specific_weight_specs_consistent(self):
        """All specific weight paraphrases should produce similar specs."""
        specs = []
        for i, phrase in enumerate(SPECIFIC_WEIGHT_PARAPHRASES[:5]):  # Sample 5
            request = TaskRequest(request_id=f"consist-{i}", user_input=phrase)
            spec = classify_task(request)
            specs.append(spec)

        # All should have same domain
        domains = [s.domain for s in specs]
        assert len(set(domains)) == 1, f"Domains should be consistent: {domains}"

        # All should include ambiguity_gate (core requirement)
        for spec in specs:
            assert "ambiguity_gate" in spec.required_gates, "Should have ambiguity_gate"


def run_tests():
    """Run all paraphrase invariance tests."""
    import traceback

    test_classes = [
        TestSpecificWeightParaphrase,
        TestLbParaphrase,
        TestUnambiguousParaphrase,
        TestFluidsParaphrase,
        TestParaphraseConsistency,
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
