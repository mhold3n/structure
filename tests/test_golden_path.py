"""
Golden path integration tests.

Tests the full flow: prompt → router → validators → kernel → response
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from router.classifier import classify_task, extract_features
from validator.gates import run_gates, ambiguity_gate, unit_consistency_gate
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
    """Test router classification."""
    
    def test_routes_to_fluids_domain(self):
        plan = classify_task("What is the specific weight of water?")
        assert plan["domain"] == "physics"
        assert plan["subdomain"] == "fluids"
    
    def test_detects_high_risk(self):
        plan = classify_task("Convert 10 lb to kg using specific weight")
        assert plan["risk_level"] in ["medium", "high"]
    
    def test_selects_unit_kernel(self):
        plan = classify_task("Convert 100 kg to pounds")
        assert "unit_converter_v1" in plan["selected_kernels"]


class TestGates:
    """Test validation gates."""
    
    def test_ambiguity_gate_clarify_on_specific_weight(self):
        """The 'specific weight of water' case should trigger CLARIFY."""
        plan = {"required_gates": ["ambiguity_gate"]}
        request = {"user_input": "What is the specific weight of water?"}
        
        decision = ambiguity_gate(plan, request)
        
        assert decision.decision == "CLARIFY"
        assert "DISALLOWED_TERM" in decision.reasons or "TERM_COLLISION" in decision.reasons
        assert len(decision.required_fields) > 0
    
    def test_ambiguity_gate_accepts_unambiguous(self):
        """Clear requests should pass."""
        plan = {"required_gates": ["ambiguity_gate"]}
        request = {"user_input": "What is 2 + 2?"}
        
        decision = ambiguity_gate(plan, request)
        
        assert decision.decision == "ACCEPT"
    
    def test_unit_gate_clarify_on_lb(self):
        """Ambiguous 'lb' unit should trigger CLARIFY."""
        plan = {"required_gates": ["unit_consistency_gate"]}
        request = {"user_input": "Convert 10 lb to kg"}
        
        decision = unit_consistency_gate(plan, request)
        
        assert decision.decision == "CLARIFY"
        assert "UNIT_AMBIGUOUS" in decision.reasons


class TestKernels:
    """Test kernel execution."""
    
    def test_units_kernel_converts_kg_to_lb(self):
        kernel = UnitsKernel()
        result = kernel.execute({
            "value": 1.0,
            "from_unit": "kg",
            "to_unit": "[lb_av]"
        })
        
        assert result.success is True
        assert abs(result.result["converted_value"] - 2.2046) < 0.001
    
    def test_constants_kernel_returns_gravity(self):
        kernel = ConstantsKernel()
        result = kernel.execute({"constant_id": "standard_gravity"})
        
        assert result.success is True
        assert result.result["value"] == 9.80665
        assert result.result["unit"] == "m/s2"
    
    def test_constants_kernel_disambiguates_water(self):
        """Searching 'specific weight water' should find the right constant."""
        kernel = ConstantsKernel()
        result = kernel.execute({"search": "specific weight"})
        
        # Should find water_specific_weight_20C
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
        2. Detect ambiguity (specific weight can mean weight density OR surface tension)
        3. Return CLARIFY with disambiguation required
        
        This is the exact failure case from the original problem description.
        """
        prompt = "What is the specific weight of water?"
        
        # Step 1: Classify
        plan = classify_task(prompt)
        assert plan["domain"] == "physics"
        assert "ambiguity_gate" in plan["required_gates"]
        
        # Step 2: Run gates
        request = {"user_input": prompt}
        gate_results = run_gates(plan, request)
        
        # Step 3: Check for CLARIFY
        clarify_gates = [g for g in gate_results if g["decision"] == "CLARIFY"]
        assert len(clarify_gates) > 0, "Should trigger CLARIFY for ambiguous term"
        
        # Step 4: Verify disambiguation fields are requested
        all_required_fields = []
        for g in clarify_gates:
            all_required_fields.extend(g.get("required_fields", []))
        
        assert len(all_required_fields) > 0, "Should request disambiguation fields"


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
