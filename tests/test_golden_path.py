"""
Golden path integration tests.

Tests the full flow: TaskRequest → router → TaskSpec → validators → kernel → response
Using typed Pydantic models throughout.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.task_spec import TaskRequest, TaskSpec, Domain, RiskLevel
from models.gate_decision import GateDecision, Decision
from router.classifier import classify_task, extract_features
from validator.gates import run_gates, get_blocking_decisions, ambiguity_gate, unit_consistency_gate
from kernels.units import UnitsKernel
from kernels.constants import ConstantsKernel


class TestFeatureExtraction:
    """Test deterministic feature extraction."""
    
    def test_detects_units(self):
        features = extract_features("The mass is 10 kg")
        assert "kg" in features["units_found"]
    
    def test_detects_equations(self):
        features = extract_features("Calculate F = ma")
        assert features["has_equations"] is True
    
    def test_detects_ambiguous_terms(self):
        features = extract_features("What is the specific weight of water?")
        assert "specific weight" in features["ambiguous_terms"]
    
    def test_classifies_physics_fluids(self):
        features = extract_features("Calculate the hydrostatic pressure at depth")
        assert "physics.fluids" in features["domain_scores"]


class TestRouter:
    """Test router classification with typed models."""
    
    def test_returns_task_spec(self):
        request = TaskRequest(
            request_id="test-1",
            user_input="What is the specific weight of water?"
        )
        spec = classify_task(request)
        assert isinstance(spec, TaskSpec)
    
    def test_routes_to_fluids_domain(self):
        request = TaskRequest(
            request_id="test-2",
            user_input="What is the specific weight of water?"
        )
        spec = classify_task(request)
        assert spec.domain == Domain.PHYSICS
        assert spec.subdomain == "fluids"
    
    def test_detects_high_risk(self):
        request = TaskRequest(
            request_id="test-3",
            user_input="Convert 10 lb to kg using specific weight and density"
        )
        spec = classify_task(request)
        assert spec.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    
    def test_selects_unit_kernel(self):
        request = TaskRequest(
            request_id="test-4",
            user_input="Convert 100 kg to pounds"
        )
        spec = classify_task(request)
        assert "unit_converter_v1" in spec.selected_kernels


class TestGates:
    """Test validation gates with typed models."""
    
    def test_returns_gate_decision(self):
        request = TaskRequest(
            request_id="test-5",
            user_input="What is the specific weight of water?"
        )
        spec = classify_task(request)
        decision = ambiguity_gate(spec)
        assert isinstance(decision, GateDecision)
    
    def test_ambiguity_gate_clarify_on_specific_weight(self):
        """The 'specific weight of water' case should trigger CLARIFY."""
        request = TaskRequest(
            request_id="test-6",
            user_input="What is the specific weight of water?"
        )
        spec = classify_task(request)
        decision = ambiguity_gate(spec)
        
        assert decision.decision == Decision.CLARIFY
        assert len(decision.reasons) > 0
        assert len(decision.required_fields) > 0
        assert len(decision.clarifying_questions) > 0
    
    def test_ambiguity_gate_accepts_unambiguous(self):
        """Clear requests should pass."""
        request = TaskRequest(
            request_id="test-7",
            user_input="What is 2 + 2?"
        )
        spec = classify_task(request)
        decision = ambiguity_gate(spec)
        
        assert decision.decision == Decision.ACCEPT
    
    def test_unit_gate_clarify_on_lb(self):
        """Ambiguous 'lb' unit should trigger CLARIFY."""
        request = TaskRequest(
            request_id="test-8",
            user_input="Convert 10 lb to kg"
        )
        spec = classify_task(request)
        decision = unit_consistency_gate(spec)
        
        assert decision.decision == Decision.CLARIFY
        assert "UNIT_AMBIGUOUS" in decision.reasons


class TestKernels:
    """Test kernel execution."""
    
    def test_units_kernel_converts_kg_to_lb(self):
        kernel = UnitsKernel()
        result = kernel.execute_legacy({
            "value": 1.0,
            "from_unit": "kg",
            "to_unit": "[lb_av]"
        })
        
        assert result.success is True
        assert abs(result.result["converted_value"] - 2.2046) < 0.001
    
    def test_constants_kernel_returns_gravity(self):
        kernel = ConstantsKernel()
        result = kernel.execute_legacy({"constant_id": "standard_gravity"})
        
        assert result.success is True
        assert result.result["value"] == 9.80665
        assert result.result["unit"] == "m/s2"
    
    def test_constants_kernel_disambiguates_water(self):
        """Searching 'specific weight' should find the right constant."""
        kernel = ConstantsKernel()
        result = kernel.execute_legacy({"search": "specific weight"})
        
        assert result.success is True
        assert "specific weight" in str(result.result).lower()


class TestGoldenPath:
    """
    Golden path regression test.
    
    This is the main integration test that proves the loop works.
    """
    
    def test_specific_weight_of_water_triggers_clarify(self):
        """
        REGRESSION TEST: 'specific weight of water' ambiguity
        
        This prompt should:
        1. Route to physics.fluids
        2. Produce a validated TaskSpec
        3. Detect ambiguity via gates
        4. Return CLARIFY with disambiguation required
        
        This is the exact failure case from the original problem description.
        """
        # Step 1: Create typed request
        request = TaskRequest(
            request_id="golden-1",
            user_input="What is the specific weight of water?"
        )
        
        # Step 2: Classify into TaskSpec
        spec = classify_task(request)
        assert isinstance(spec, TaskSpec)
        assert spec.domain == Domain.PHYSICS
        assert "ambiguity_gate" in spec.required_gates
        
        # Step 3: Run gates
        gate_results = run_gates(spec)
        assert all(isinstance(g, GateDecision) for g in gate_results)
        
        # Step 4: Check for blocking decisions
        blocking = get_blocking_decisions(gate_results)
        assert len(blocking) > 0, "Should trigger CLARIFY for ambiguous term"
        
        # Step 5: Verify clarification details
        clarify_decision = blocking[0]
        assert clarify_decision.decision == Decision.CLARIFY
        assert len(clarify_decision.required_fields) > 0
        assert len(clarify_decision.clarifying_questions) > 0
    
    def test_unambiguous_request_passes(self):
        """Clear requests should pass all gates."""
        request = TaskRequest(
            request_id="golden-2",
            user_input="Calculate the area of a circle with radius 5 meters"
        )
        
        spec = classify_task(request)
        gate_results = run_gates(spec)
        blocking = get_blocking_decisions(gate_results)
        
        assert len(blocking) == 0, "Should not block on unambiguous request"


def run_tests():
    """Run all tests and print results."""
    import traceback
    
    test_classes = [
        TestFeatureExtraction,
        TestRouter,
        TestGates,
        TestKernels,
        TestGoldenPath,
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running: {test_class.__name__}")
        print('='*60)
        
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
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('='*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
