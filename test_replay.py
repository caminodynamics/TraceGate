from decision_engine import DecisionEngine, DecisionInputs
from mutation_simulator import MutationSimulator


def test_no_mutation_replay_matches():
    """Test case 1: No mutation → replay must match"""
    print("\n=== Test 1: No Mutation ===")
    
    engine = DecisionEngine()
    
    # Create inputs that should ALLOW
    inputs: DecisionInputs = {
        "user_tier": "premium",
        "region": "EU",
        "feature_flag_safe_mode": True
    }
    
    # Generate artifact
    artifact = engine.generate_artifact(inputs)
    print(f"Original decision: {artifact['decision']}")
    print(f"Artifact: {artifact}")
    
    # Replay without mutation
    replayed_decision, status = engine.replay(artifact)
    print(f"Replayed decision: {replayed_decision}")
    print(f"Status: {status}")
    
    # Assert match
    assert status == "MATCH", f"Expected MATCH, got {status}"
    assert replayed_decision == artifact["decision"], f"Decision mismatch: {replayed_decision} != {artifact['decision']}"
    
    print("[PASS] Test 1 PASSED: Replay matches original decision")


def test_feature_flag_change_detects_mismatch():
    """Test case 2: Feature flag changes → must detect mismatch or explain failure"""
    print("\n=== Test 2: Feature Flag Mutation ===")
    
    engine = DecisionEngine()
    
    # Create inputs that should ALLOW
    inputs: DecisionInputs = {
        "user_tier": "premium",
        "region": "EU",
        "feature_flag_safe_mode": True
    }
    
    # Generate artifact
    artifact = engine.generate_artifact(inputs)
    print(f"Original decision: {artifact['decision']}")
    print(f"Original feature_flag_safe_mode: {artifact['inputs']['feature_flag_safe_mode']}")
    
    # Mutate feature flag
    mutated_artifact = MutationSimulator.mutate_feature_flag(artifact, False)
    print(f"Mutated feature_flag_safe_mode: {mutated_artifact['inputs']['feature_flag_safe_mode']}")
    
    # Replay with mutated artifact
    replayed_decision, status = engine.replay(mutated_artifact)
    print(f"Replayed decision: {replayed_decision}")
    print(f"Status: {status}")
    
    # Assert mismatch detected
    assert status == "INPUT_MISMATCH", f"Expected INPUT_MISMATCH, got {status}"
    assert replayed_decision != artifact["decision"], f"Expected decision change, but got same: {replayed_decision}"
    
    print("[PASS] Test 2 PASSED: Feature flag mutation detected")


def test_policy_change_detects_mismatch():
    """Test case 3: Policy changes → must detect mismatch or explain failure"""
    print("\n=== Test 3: Policy Mutation ===")
    
    engine = DecisionEngine()
    
    # Create inputs that should ALLOW
    inputs: DecisionInputs = {
        "user_tier": "premium",
        "region": "EU",
        "feature_flag_safe_mode": True
    }
    
    # Generate artifact
    artifact = engine.generate_artifact(inputs)
    print(f"Original decision: {artifact['decision']}")
    print(f"Original policy hash: {artifact['policy_version_hash'][:16]}...")
    
    # Mutate policy hash
    mutated_artifact = MutationSimulator.mutate_policy_hash(artifact)
    print(f"Mutated policy hash: {mutated_artifact['policy_version_hash'][:16]}...")
    
    # Replay with mutated artifact
    replayed_decision, status = engine.replay(mutated_artifact)
    print(f"Replayed decision: {replayed_decision}")
    print(f"Status: {status}")
    
    # Assert policy mismatch detected
    assert status == "POLICY_MISMATCH", f"Expected POLICY_MISMATCH, got {status}"
    assert replayed_decision == "UNKNOWN", f"Expected UNKNOWN decision, got {replayed_decision}"
    
    print("[PASS] Test 3 PASSED: Policy mutation detected")


if __name__ == "__main__":
    test_no_mutation_replay_matches()
    test_feature_flag_change_detects_mismatch()
    test_policy_change_detects_mismatch()
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED")
    print("="*50)
