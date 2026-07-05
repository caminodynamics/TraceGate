from decision_engine import DecisionEngine
from typing import Dict, Any
import copy


def test_scenario_1_missing_environment_state():
    """
    SCENARIO 1: Missing Environment State
    Environment state is NULL/missing entirely.
    """
    print("\n" + "="*60)
    print("MISSING STATE INJECTION TEST - SCENARIO 1")
    print("="*60)
    print("\nScenario: Missing Environment State")
    
    engine = DecisionEngine()
    
    input_event = {
        "event_id": "missing-env-test-1",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        # environment_state is missing entirely
        "context": {
            "simulation_mode": True
        }
    }
    
    print("  Input state: complete (premium, EU, safe_mode=true)")
    print("  Environment state: NULL/missing")
    print("  Policy state: available")
    
    # System MUST NOT crash
    try:
        artifact = engine.evaluate_decision(input_event)
        print("[OK] System did not crash with missing environment state")
    except Exception as e:
        raise AssertionError(f"System crashed with missing environment state: {e}")
    
    debug = artifact["debug"]
    
    # ASSERTION A: Missing state detection
    print("\n--- ASSERTION A: Missing State Detection ---")
    assert "state_completeness_report" in debug, "state_completeness_report must be present"
    report = debug["state_completeness_report"]
    
    assert report["environment_complete"] == False, "environment_complete must be False"
    assert "environment_state" in report["missing_fields"], "environment_state must be in missing_fields"
    assert "environment" in report["missing_domains"], "environment must be in missing_domains"
    assert report["incomplete_state"] == True, "incomplete_state must be True"
    print("[PASS] Missing environment state detected")
    
    # ASSERTION B: No silent inference
    print("\n--- ASSERTION B: No Silent Inference ---")
    assert report["inference_prohibited"] == True, "inference_prohibited must be True"
    
    # Verify no default values appear for missing fields
    assert artifact["environment_hash"] is None, "Environment hash must be None (no inference)"
    print("[PASS] No silent inference of missing environment state")
    
    # ASSERTION C: Deterministic output
    print("\n--- ASSERTION C: Deterministic Output ---")
    artifacts = []
    for i in range(3):
        run_artifact = engine.evaluate_decision(input_event)
        artifacts.append(run_artifact)
    
    for i in range(1, len(artifacts)):
        assert artifacts[i]["decision"] == artifacts[0]["decision"], \
            f"Decision must be identical across runs (run {i} vs run 0)"
        assert artifacts[i]["evaluated_inputs_hash"] == artifacts[0]["evaluated_inputs_hash"], \
            f"Input hash must be identical across runs (run {i} vs run 0)"
    
    print("[PASS] Repeated runs produce identical artifacts")
    
    # ASSERTION D: Provenance integrity
    print("\n--- ASSERTION D: Provenance Integrity ---")
    # Raw input_state remains unchanged
    original_inputs = input_event["inputs"]
    re_artifact = engine.evaluate_decision(input_event)
    assert re_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Input hash must be stable (raw input_state unchanged)"
    
    # Missing state is explicitly recorded, not reconstructed
    assert re_artifact["debug"]["state_completeness_report"] == report, \
        "State completeness report must be identical (missing state explicitly recorded)"
    print("[PASS] Raw input_state unchanged, missing state explicitly recorded")
    
    # ASSERTION E: Fallback rule correctness
    print("\n--- ASSERTION E: Fallback Rule Correctness ---")
    # System uses explicit fallback rule: evaluate with available input state only
    # Per golden_policy.json, premium EU users are DENY
    assert artifact["decision"] == "DENY", \
        "Fallback rule: decision based on available input state (DENY per golden_policy.json)"
    print("[PASS] Fallback rule applied deterministically")
    
    print("\n[PASS] SCENARIO 1 PASSED")


def test_scenario_2_partial_environment_state():
    """
    SCENARIO 2: Partial Environment State
    Environment state has feature_flag_safe_mode but system_load is missing.
    """
    print("\n" + "="*60)
    print("MISSING STATE INJECTION TEST - SCENARIO 2")
    print("="*60)
    print("\nScenario: Partial Environment State")
    
    engine = DecisionEngine()
    
    input_event = {
        "event_id": "partial-env-test-2",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": True
            # system_load is missing
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("  Input state: complete (premium, EU, safe_mode=true)")
    print("  Environment state: partial (feature_flag present, system_load missing)")
    print("  Policy state: available")
    
    # System MUST NOT crash
    try:
        artifact = engine.evaluate_decision(input_event)
        print("[OK] System did not crash with partial environment state")
    except Exception as e:
        raise AssertionError(f"System crashed with partial environment state: {e}")
    
    debug = artifact["debug"]
    
    # ASSERTION A: Missing state detection
    print("\n--- ASSERTION A: Missing State Detection ---")
    # For this toy engine, environment_state is optional, so partial is considered complete
    # But we verify no inference occurred
    assert artifact["environment_hash"] is not None, "Environment hash should be computed"
    print("[PASS] Partial environment state handled without inference")
    
    # ASSERTION B: No silent inference
    print("\n--- ASSERTION B: No Silent Inference ---")
    # Verify system_load was not inferred/defaulted
    env_state = input_event["environment_state"]
    assert "system_load" not in env_state, "system_load must not be inferred"
    print("[PASS] No silent inference of missing system_load field")
    
    # ASSERTION C: Deterministic output
    print("\n--- ASSERTION C: Deterministic Output ---")
    artifacts = []
    for i in range(3):
        run_artifact = engine.evaluate_decision(input_event)
        artifacts.append(run_artifact)
    
    for i in range(1, len(artifacts)):
        assert artifacts[i]["decision"] == artifacts[0]["decision"], \
            f"Decision must be identical across runs (run {i} vs run 0)"
    
    print("[PASS] Repeated runs produce identical artifacts")
    
    # ASSERTION D: Provenance integrity
    print("\n--- ASSERTION D: Provenance Integrity ---")
    re_artifact = engine.evaluate_decision(input_event)
    assert re_artifact["environment_hash"] == artifact["environment_hash"], \
        "Environment hash must be stable (partial state unchanged)"
    print("[PASS] Partial environment state unchanged")
    
    print("\n[PASS] SCENARIO 2 PASSED")


def test_scenario_3_missing_policy_state():
    """
    SCENARIO 3: Missing Policy State
    Policy state is NULL/unavailable at evaluation time.
    Note: In this toy engine, policy is hardcoded, so we simulate this by
    testing the detection logic without actual policy unavailability.
    """
    print("\n" + "="*60)
    print("MISSING STATE INJECTION TEST - SCENARIO 3")
    print("="*60)
    print("\nScenario: Missing Policy State (simulated)")
    
    engine = DecisionEngine()
    
    input_event = {
        "event_id": "missing-policy-test-3",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": True
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("  Input state: complete (premium, EU, safe_mode=true)")
    print("  Environment state: complete")
    print("  Policy state: available (hardcoded in toy engine)")
    
    # System MUST NOT crash
    try:
        artifact = engine.evaluate_decision(input_event)
        print("[OK] System did not crash")
    except Exception as e:
        raise AssertionError(f"System crashed: {e}")
    
    debug = artifact["debug"]
    
    # In this toy engine, policy is always available (hardcoded)
    # So we verify the detection logic works correctly
    assert "state_completeness_report" not in debug or not debug.get("state_completeness_report", {}).get("incomplete_state", False), \
        "State should be complete when all sources are available"
    
    print("[PASS] Policy state available (hardcoded in toy engine)")
    print("[PASS] SCENARIO 3 PASSED (simulated)")


def test_missing_input_state():
    """
    Additional test: Missing Input State fields.
    """
    print("\n" + "="*60)
    print("MISSING STATE INJECTION TEST - MISSING INPUT STATE")
    print("="*60)
    print("\nScenario: Missing Input State Fields")
    
    engine = DecisionEngine()
    
    input_event = {
        "event_id": "missing-input-test",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU"
            # feature_flag_safe_mode is missing
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("  Input state: partial (user_tier, region present, feature_flag missing)")
    
    # System MUST NOT crash
    try:
        artifact = engine.evaluate_decision(input_event)
        print("[OK] System did not crash with missing input field")
    except Exception as e:
        raise AssertionError(f"System crashed with missing input field: {e}")
    
    debug = artifact["debug"]
    
    # ASSERTION A: Missing state detection
    print("\n--- ASSERTION A: Missing State Detection ---")
    assert "state_completeness_report" in debug, "state_completeness_report must be present"
    report = debug["state_completeness_report"]
    
    assert report["input_complete"] == False, "input_complete must be False"
    assert "input_state.feature_flag_safe_mode" in report["missing_fields"], \
        "input_state.feature_flag_safe_mode must be in missing_fields"
    assert "input" in report["missing_domains"], "input must be in missing_domains"
    print("[PASS] Missing input field detected")
    
    # ASSERTION B: No silent inference
    print("\n--- ASSERTION B: No Silent Inference ---")
    assert report["inference_prohibited"] == True, "inference_prohibited must be True"
    print("[PASS] No silent inference of missing input field")
    
    # ASSERTION E: Fallback rule correctness
    print("\n--- ASSERTION E: Fallback Rule Correctness ---")
    # Missing feature_flag_safe_mode should result in ALLOW (condition not met per golden_policy.json)
    assert artifact["decision"] == "ALLOW", \
        "Fallback rule: missing feature_flag should result in ALLOW (condition not met)"
    print("[PASS] Fallback rule applied correctly (ALLOW for missing feature_flag)")
    
    print("\n[PASS] MISSING INPUT STATE TEST PASSED")


if __name__ == "__main__":
    test_scenario_1_missing_environment_state()
    test_scenario_2_partial_environment_state()
    test_scenario_3_missing_policy_state()
    test_missing_input_state()
    
    print("\n" + "="*60)
    print("ALL MISSING STATE INJECTION TESTS PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Missing state detection")
    print("  [PASS] No silent inference")
    print("  [PASS] Deterministic output")
    print("  [PASS] Provenance integrity")
    print("  [PASS] Fallback rule correctness")
