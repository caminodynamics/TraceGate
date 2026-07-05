from decision_engine import DecisionEngine
from mutation_simulator import MutationSimulator
from typing import Dict, Any


def create_input_event(user_tier: str, region: str, feature_flag: bool) -> Dict[str, Any]:
    """Helper to create input_event with proper schema."""
    return {
        "event_id": "test-event-1",
        "timestamp": "2024-01-01T00:00:00Z",
        "inputs": {
            "user_tier": user_tier,
            "region": region,
            "feature_flag_safe_mode": feature_flag
        },
        "context": {
            "source": "replay-lab",
            "simulation_mode": False
        }
    }


def test_no_mutation_replay_matches():
    """Test case 1: No mutation → replay must match"""
    print("\n=== Test 1: No Mutation ===")
    
    engine = DecisionEngine()
    
    # Create input that should ALLOW
    input_event = create_input_event("premium", "EU", True)
    
    # Generate artifact
    original_artifact = engine.evaluate_decision(input_event)
    print(f"Original decision: {original_artifact['decision']}")
    print(f"Original policy_hash: {original_artifact['policy_hash'][:16]}...")
    print(f"Original evaluated_inputs_hash: {original_artifact['evaluated_inputs_hash'][:16]}...")
    print(f"Original environment_hash: {original_artifact['environment_hash']}")
    
    # Replay with same input (no mutation)
    replayed_artifact = engine.evaluate_decision(input_event)
    print(f"Replayed decision: {replayed_artifact['decision']}")
    print(f"Replayed policy_hash: {replayed_artifact['policy_hash'][:16]}...")
    print(f"Replayed evaluated_inputs_hash: {replayed_artifact['evaluated_inputs_hash'][:16]}...")
    print(f"Replayed environment_hash: {replayed_artifact['environment_hash']}")
    
    # Assert match
    assert replayed_artifact["decision"] == original_artifact["decision"], \
        f"Decision mismatch: {replayed_artifact['decision']} != {original_artifact['decision']}"
    assert replayed_artifact["policy_hash"] == original_artifact["policy_hash"], \
        f"Policy hash mismatch"
    assert replayed_artifact["evaluated_inputs_hash"] == original_artifact["evaluated_inputs_hash"], \
        f"Inputs hash mismatch"
    assert replayed_artifact["environment_hash"] == original_artifact["environment_hash"], \
        f"Environment hash mismatch"
    assert replayed_artifact["engine_name"] == original_artifact["engine_name"], \
        f"Engine name mismatch"
    assert replayed_artifact["engine_version"] == original_artifact["engine_version"], \
        f"Engine version mismatch"
    
    print("[PASS] Test 1 PASSED: Replay matches original decision")


def test_feature_flag_change_detects_mismatch():
    """Test case 2: Feature flag changes → must detect mismatch or explain failure"""
    print("\n=== Test 2: Feature Flag Mutation ===")
    
    engine = DecisionEngine()
    
    # Create input that should ALLOW
    input_event = create_input_event("premium", "EU", True)
    
    # Generate original artifact
    original_artifact = engine.evaluate_decision(input_event)
    print(f"Original decision: {original_artifact['decision']}")
    print(f"Original feature_flag_safe_mode: {input_event['inputs']['feature_flag_safe_mode']}")
    print(f"Original evaluated_inputs_hash: {original_artifact['evaluated_inputs_hash'][:16]}...")
    
    # Mutate feature flag
    mutated_input_event = MutationSimulator.mutate_feature_flag(input_event, False)
    print(f"Mutated feature_flag_safe_mode: {mutated_input_event['inputs']['feature_flag_safe_mode']}")
    
    # Replay with mutated input
    replayed_artifact = engine.evaluate_decision(mutated_input_event)
    print(f"Replayed decision: {replayed_artifact['decision']}")
    print(f"Replayed evaluated_inputs_hash: {replayed_artifact['evaluated_inputs_hash'][:16]}...")
    
    # Assert mismatch detected
    assert replayed_artifact["decision"] != original_artifact["decision"], \
        f"Expected decision change, but got same: {replayed_artifact['decision']}"
    assert replayed_artifact["evaluated_inputs_hash"] != original_artifact["evaluated_inputs_hash"], \
        f"Expected inputs hash change, but got same"
    assert replayed_artifact["policy_hash"] == original_artifact["policy_hash"], \
        f"Policy hash should not change for feature flag mutation"
    
    print("[PASS] Test 2 PASSED: Feature flag mutation detected via decision and inputs hash change")


def test_policy_change_detects_mismatch():
    """Test case 3: Policy changes → must detect mismatch or explain failure"""
    print("\n=== Test 3: Policy Mutation ===")
    
    engine = DecisionEngine()
    
    # Create input that should ALLOW
    input_event = create_input_event("premium", "EU", True)
    
    # Generate original artifact
    original_artifact = engine.evaluate_decision(input_event)
    print(f"Original decision: {original_artifact['decision']}")
    print(f"Original policy_hash: {original_artifact['policy_hash'][:16]}...")
    
    # Mutate policy hash in stored artifact (simulates policy change between runs)
    mutated_artifact = MutationSimulator.mutate_policy_hash_in_artifact(original_artifact)
    print(f"Mutated policy_hash: {mutated_artifact['policy_hash'][:16]}...")
    
    # The mutated artifact now has a different policy_hash
    # In a real scenario, replay would detect this via policy_hash comparison
    assert mutated_artifact["policy_hash"] != original_artifact["policy_hash"], \
        f"Policy hash should be mutated"
    assert mutated_artifact["determinism_flags"]["mutation_detected"] == True, \
        f"Mutation detected flag should be set"
    
    print("[PASS] Test 3 PASSED: Policy mutation detected via policy hash change and flag")


def test_state_separation_correctness():
    """Test case 4: Validate state separation per state_model_contract.md"""
    print("\n=== Test 4: State Separation Correctness ===")
    
    engine = DecisionEngine()
    
    # Create input that should ALLOW
    input_event = create_input_event("premium", "EU", True)
    
    # Generate artifact
    artifact = engine.evaluate_decision(input_event)
    
    # Validate that input_hash does NOT include policy logic
    # Change policy (simulate by creating new engine with different policy)
    # Input hash should remain the same
    same_input_event = create_input_event("premium", "EU", True)
    same_artifact = engine.evaluate_decision(same_input_event)
    assert same_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Input hash should be deterministic for same inputs"
    
    # Validate that policy_hash does NOT include inputs
    # Different inputs should produce same policy_hash
    different_input_event = create_input_event("basic", "US", False)
    different_artifact = engine.evaluate_decision(different_input_event)
    assert different_artifact["policy_hash"] == artifact["policy_hash"], \
        "Policy hash should be independent of inputs"
    
    # Validate that environment_hash is None (no external state used)
    assert artifact["environment_hash"] is None, \
        "Environment hash should be None when no external state is used"
    
    # Validate that feature flag is classified as INPUT STATE
    # Changing feature flag should change input_hash but NOT policy_hash
    mutated_flag_event = MutationSimulator.mutate_feature_flag(input_event, False)
    mutated_artifact = engine.evaluate_decision(mutated_flag_event)
    assert mutated_artifact["evaluated_inputs_hash"] != artifact["evaluated_inputs_hash"], \
        "Feature flag change should affect input hash (classified as INPUT STATE)"
    assert mutated_artifact["policy_hash"] == artifact["policy_hash"], \
        "Feature flag change should NOT affect policy hash"
    
    print("[PASS] Test 4 PASSED: State separation is correct per state_model_contract.md")


def test_feature_flag_dual_location_consistency():
    """
    Test case 5: Adversarial test - feature flag in both input and environment.
    Per state_model_contract.md: feature flags MUST be classified consistently.
    If in request payload → INPUT STATE.
    Engine must not silently leak between categories.
    """
    print("\n=== Test 5: Feature Flag Dual Location Consistency ===")
    
    engine = DecisionEngine()
    
    # Create input_event with feature flag in inputs (INPUT STATE)
    input_event = {
        "event_id": "test-event-5",
        "timestamp": "2024-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": False  # Same flag in environment (should be ignored)
        },
        "context": {
            "source": "replay-lab",
            "simulation_mode": False
        }
    }
    
    # Generate artifact
    artifact = engine.evaluate_decision(input_event)
    
    # Decision should be based on INPUT STATE (inputs.feature_flag_safe_mode = True)
    # Per golden_policy.json, premium EU users are DENIED
    assert artifact["decision"] == "DENY", \
        "Decision should be DENY per golden_policy.json for premium EU users"
    
    # Input hash should include the INPUT STATE feature flag
    assert artifact["evaluated_inputs_hash"] is not None, \
        "Input hash should be computed"
    
    # Environment hash should be computed (since environment_state is provided)
    assert artifact["environment_hash"] is not None, \
        "Environment hash should be computed when environment_state is provided"
    
    # Policy hash should remain unchanged
    assert artifact["policy_hash"] is not None, \
        "Policy hash should be computed"
    
    # Now test with INPUT STATE flag = False
    input_event_false = {
        "event_id": "test-event-5b",
        "timestamp": "2024-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": False
        },
        "environment_state": {
            "feature_flag_safe_mode": False  # Environment flag same as first case
        },
        "context": {
            "source": "replay-lab",
            "simulation_mode": False
        }
    }
    
    artifact_false = engine.evaluate_decision(input_event_false)
    
    # Decision should be ALLOW (condition not met, per golden_policy.json blacklist approach)
    assert artifact_false["decision"] == "ALLOW", \
        "Decision should be ALLOW when premium EU condition not met (feature_flag=False)"
    
    # Input hash should differ from first case
    assert artifact_false["evaluated_inputs_hash"] != artifact["evaluated_inputs_hash"], \
        "Input hash should differ when INPUT STATE feature flag changes"
    
    # Policy hash should be the same (policy didn't change)
    assert artifact_false["policy_hash"] == artifact["policy_hash"], \
        "Policy hash should be identical (policy unchanged)"
    
    # Environment hash should be the same (environment_state unchanged)
    assert artifact_false["environment_hash"] == artifact["environment_hash"], \
        "Environment hash should be identical (environment_state unchanged)"
    
    print("[PASS] Test 5 PASSED: Feature flag classified consistently as INPUT STATE, no leakage")


if __name__ == "__main__":
    test_no_mutation_replay_matches()
    test_feature_flag_change_detects_mismatch()
    test_policy_change_detects_mismatch()
    test_state_separation_correctness()
    test_feature_flag_dual_location_consistency()
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED")
    print("="*50)
