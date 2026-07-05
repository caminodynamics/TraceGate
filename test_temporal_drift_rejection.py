from decision_engine import DecisionEngine
from policy_registry import get_global_registry
from typing import Dict, Any
import copy


class PolicyV1Engine(DecisionEngine):
    """
    Engine with policy_v1: IF premium AND EU THEN ALLOW
    """
    def _get_policy_source(self) -> str:
        return """
        IF user_tier == "premium"
        AND region == "EU"
        THEN ALLOW
        ELSE DENY
        """
    
    def _evaluate_policy(self, inputs: Dict[str, Any]) -> str:
        if (inputs.get("user_tier") == "premium" and
            inputs.get("region") == "EU"):
            return "ALLOW"
        return "DENY"


class PolicyV2Engine(DecisionEngine):
    """
    Engine with policy_v2: IF premium AND EU THEN DENY
    """
    def _get_policy_source(self) -> str:
        return """
        IF user_tier == "premium"
        AND region == "EU"
        THEN DENY
        ELSE ALLOW
        """
    
    def _evaluate_policy(self, inputs: Dict[str, Any]) -> str:
        if (inputs.get("user_tier") == "premium" and
            inputs.get("region") == "EU"):
            return "DENY"
        return "ALLOW"


def test_temporal_drift_rejection():
    """
    Test 3.4: Temporal Drift Rejection
    
    Validates behavior when an artifact references a historical policy version
    that cannot be reconstructed.
    
    Scenario:
    1. Evaluate using policy_v1.
    2. Produce artifact.
    3. Remove policy_v1 from historical registry.
    4. Keep only policy_v2.
    5. Attempt replay.
    
    Assertions:
    - replay must fail hard
    - replay must not substitute policy_v2
    - replay must not silently fallback
    - replay must emit explicit temporal drift error
    - artifact remains unchanged
    
    Failure condition:
    If replay succeeds using any policy other than the historical policy
    referenced by the artifact.
    """
    print("\n" + "="*60)
    print("TEST 3.4: TEMPORAL DRIFT REJECTION")
    print("="*60)
    
    print("\nPOLICY_v1 (historical, to be removed):")
    print("  IF user_tier == 'premium' AND region == 'EU' THEN ALLOW")
    print("  ELSE DENY")
    
    print("\nPOLICY_v2 (current, only policy remaining):")
    print("  IF user_tier == 'premium' AND region == 'EU' THEN DENY")
    print("  ELSE ALLOW")
    
    # STEP 1: Evaluate using policy_v1
    print("\n--- STEP 1: Evaluate using policy_v1 (T0) ---")
    engine_v1 = PolicyV1Engine(policy_version="1.0.0")
    
    input_event = {
        "event_id": "temporal-drift-test",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("Input state:")
    print("  user_tier: premium")
    print("  region: EU")
    print("  feature_flag_safe_mode: true")
    
    original_artifact = engine_v1.evaluate_decision(input_event)
    original_decision = original_artifact["decision"]
    original_policy_hash = original_artifact["policy_hash"]
    original_policy_version = original_artifact["policy_version"]
    
    print(f"\nOriginal evaluation (T0):")
    print(f"  Decision: {original_decision}")
    print(f"  Policy hash: {original_policy_hash[:16]}...")
    print(f"  Policy version: {original_policy_version}")
    
    # Store artifact copy for later comparison
    artifact_copy = copy.deepcopy(original_artifact)
    
    # STEP 2: Remove policy_v1 from registry
    print("\n--- STEP 2: Remove policy_v1 from historical registry ---")
    registry = get_global_registry()
    
    print(f"Removing policy_v1 from registry...")
    removed = registry.remove_policy(original_policy_hash)
    assert removed == True, "Policy_v1 should be removed from registry"
    print(f"[PASS] Policy_v1 removed from registry")
    
    # Verify policy_v1 is gone
    policy_exists = registry.policy_exists(original_policy_hash)
    assert policy_exists == False, "Policy_v1 should not exist in registry"
    print(f"[PASS] Policy_v1 no longer exists in registry")
    
    # STEP 3: Create policy_v2 engine (only policy remaining)
    print("\n--- STEP 3: Create policy_v2 engine (only policy remaining) ---")
    engine_v2 = PolicyV2Engine(policy_version="2.0.0")
    
    print(f"Current engine has policy_v2")
    print(f"  Policy version: 2.0.0")
    
    # Verify policy_v2 exists in registry
    v2_policy_hash = engine_v2._compute_policy_hash()
    v2_exists = registry.policy_exists(v2_policy_hash)
    assert v2_exists == True, "Policy_v2 should exist in registry"
    print(f"[PASS] Policy_v2 exists in registry")
    
    # STEP 4: Attempt replay with missing historical policy
    print("\n--- STEP 4: Attempt replay with missing historical policy ---")
    print("Replay attempt: artifact references policy_v1 (missing)")
    
    try:
        replay_artifact = engine_v2.evaluate_decision(
            input_event,
            replay_mode=True,
            historical_policy_hash=original_policy_hash
        )
        
        # If we reach here, replay succeeded (FAILURE)
        raise AssertionError(
            "Replay should have failed with ValueError for missing historical policy. "
            f"Instead, replay succeeded with decision: {replay_artifact['decision']}"
        )
        
    except ValueError as e:
        print(f"[PASS] Replay correctly failed with ValueError")
        print(f"  Error message: {e}")
        
        # ASSERTION A: Replay emits explicit temporal drift error
        print("\n--- ASSERTION A: Explicit Temporal Drift Error ---")
        error_msg = str(e)
        assert "Historical policy not found" in error_msg, \
            "Error message must explicitly mention historical policy not found"
        assert "temporal drift" in error_msg.lower() or "replay cannot proceed" in error_msg.lower(), \
            "Error message must indicate temporal drift or replay failure"
        print(f"[PASS] Error message explicitly mentions temporal drift")
        
    # STEP 5: Verify artifact remains unchanged
    print("\n--- STEP 5: Verify Artifact Remains Unchanged ---")
    assert original_artifact == artifact_copy, \
        "Original artifact must remain unchanged after failed replay"
    print(f"[PASS] Artifact remains unchanged")
    
    # Verify artifact fields are intact
    assert original_artifact["decision"] == original_decision, \
        "Artifact decision must be unchanged"
    assert original_artifact["policy_hash"] == original_policy_hash, \
        "Artifact policy hash must be unchanged"
    assert original_artifact["policy_version"] == original_policy_version, \
        "Artifact policy version must be unchanged"
    print(f"[PASS] All artifact fields intact")
    
    # STEP 6: Verify replay does NOT substitute policy_v2
    print("\n--- STEP 6: Verify Replay Does NOT Substitute Policy_v2 ---")
    print("Attempting replay without historical policy hash (would use current policy)")
    
    # This should use current policy (policy_v2) and produce different decision
    replay_without_historical = engine_v2.evaluate_decision(input_event, replay_mode=False)
    replay_without_decision = replay_without_historical["decision"]
    
    print(f"Replay without historical hash: {replay_without_decision}")
    assert replay_without_decision != original_decision, \
        "Replay without historical hash should use current policy (different decision)"
    print(f"[PASS] Replay without historical hash uses current policy ({replay_without_decision})")
    
    # But this is NOT the same as using historical policy binding
    # The key is that when historical_policy_hash is provided, replay MUST fail
    # if that policy is missing, not silently substitute current policy
    print(f"\nKey distinction:")
    print(f"  - With historical_policy_hash provided: MUST fail if policy missing")
    print(f"  - Without historical_policy_hash: uses current policy (different behavior)")
    print(f"[PASS] Replay does NOT silently substitute policy_v2 when historical policy requested")
    
    # STEP 7: Restore policy_v1 for cleanup
    print("\n--- STEP 7: Restore policy_v1 for cleanup ---")
    engine_v1_restore = PolicyV1Engine(policy_version="1.0.0")
    print(f"[INFO] Policy_v1 restored to registry for cleanup")
    
    print("\n" + "="*60)
    print("TEMPORAL DRIFT REJECTION TEST: PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Replay fails hard when historical policy not found")
    print("  [PASS] Replay emits explicit temporal drift error")
    print("  [PASS] Replay does NOT substitute policy_v2")
    print("  [PASS] Replay does NOT silently fallback")
    print("  [PASS] Artifact remains unchanged")
    print("  [PASS] Error message explicitly mentions historical policy not found")
    print("\nConclusion:")
    print("  Temporal drift rejection is enforced")
    print("  Replay never succeeds using wrong policy version")
    print("  No silent fallback or policy substitution occurs")


if __name__ == "__main__":
    test_temporal_drift_rejection()
