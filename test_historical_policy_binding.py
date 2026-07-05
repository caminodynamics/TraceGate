from decision_engine import DecisionEngine
from policy_registry import get_global_registry
from typing import Dict, Any
import hashlib


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


def test_historical_policy_binding():
    """
    Historical Policy Binding Test
    
    Validates that replay uses historical policy from artifact and never current policy.
    
    Assertions:
    - replay(policy_v1 artifact) == policy_v1 decision
    - replay must fail if historical policy cannot be resolved
    - replay must never silently substitute current policy
    """
    print("\n" + "="*60)
    print("HISTORICAL POLICY BINDING TEST")
    print("="*60)
    
    print("\nPOLICY_v1 (original at T0):")
    print("  IF user_tier == 'premium' AND region == 'EU' THEN ALLOW")
    print("  ELSE DENY")
    
    print("\nPOLICY_v2 (current at T1):")
    print("  IF user_tier == 'premium' AND region == 'EU' THEN DENY")
    print("  ELSE ALLOW")
    
    # STEP 1: Evaluate with policy_v1
    print("\n--- STEP 1: Evaluate with policy_v1 (T0) ---")
    engine_v1 = PolicyV1Engine(policy_version="1.0.0")
    
    input_event = {
        "event_id": "historical-binding-test",
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
    original_policy_snapshot_ref = original_artifact["policy_snapshot_reference"]
    
    print(f"\nOriginal evaluation (T0):")
    print(f"  Decision: {original_decision}")
    print(f"  Policy hash: {original_policy_hash[:16]}...")
    print(f"  Policy version: {original_policy_version}")
    print(f"  Policy snapshot reference: {original_policy_snapshot_ref[:16]}...")
    
    # STEP 2: Mutate to policy_v2
    print("\n--- STEP 2: Mutate to policy_v2 (T1) ---")
    engine_v2 = PolicyV2Engine(policy_version="2.0.0")
    
    print(f"Current engine now has policy_v2")
    print(f"  Policy version: 2.0.0")
    
    # STEP 3: Replay with historical policy binding
    print("\n--- STEP 3: Replay with historical policy binding ---")
    print("Replay using historical policy hash from artifact")
    
    replay_artifact = engine_v2.evaluate_decision(
        input_event,
        replay_mode=True,
        historical_policy_hash=original_policy_hash
    )
    
    replay_decision = replay_artifact["decision"]
    replay_policy_hash = replay_artifact["policy_hash"]
    replay_policy_version = replay_artifact["policy_version"]
    
    print(f"\nReplay result:")
    print(f"  Decision: {replay_decision}")
    print(f"  Policy hash used: {replay_policy_hash[:16]}...")
    print(f"  Policy version: {replay_policy_version}")
    
    # ASSERTION A: Replay decision matches original decision
    print("\n--- ASSERTION A: Replay Decision Matches Original ---")
    assert replay_decision == original_decision, \
        f"Replay decision must match original decision: {replay_decision} != {original_decision}"
    print(f"[PASS] Replay decision == Original decision ({original_decision})")
    
    # ASSERTION B: Replay uses historical policy hash
    print("\n--- ASSERTION B: Replay Uses Historical Policy Hash ---")
    assert replay_policy_hash == original_policy_hash, \
        f"Replay must use historical policy hash: {replay_policy_hash} != {original_policy_hash}"
    print(f"[PASS] Replay uses historical policy hash")
    
    # ASSERTION C: Replay uses historical policy version
    print("\n--- ASSERTION C: Replay Uses Historical Policy Version ---")
    assert replay_policy_version == original_policy_version, \
        f"Replay must use historical policy version: {replay_policy_version} != {original_policy_version}"
    print(f"[PASS] Replay uses historical policy version ({original_policy_version})")
    
    # ASSERTION D: Replay does NOT use current policy
    print("\n--- ASSERTION D: Replay Does Not Use Current Policy ---")
    current_policy_hash = engine_v2._compute_policy_hash()
    assert replay_policy_hash != current_policy_hash, \
        "Replay must NOT use current policy hash"
    print(f"[PASS] Replay does NOT use current policy hash")
    
    # STEP 4: Test replay failure when historical policy not found
    print("\n--- STEP 4: Test Replay Failure When Historical Policy Not Found ---")
    fake_policy_hash = "0" * 64  # Non-existent hash
    
    try:
        engine_v2.evaluate_decision(
            input_event,
            replay_mode=True,
            historical_policy_hash=fake_policy_hash
        )
        raise AssertionError("Replay should fail when historical policy not found")
    except ValueError as e:
        print(f"[PASS] Replay correctly failed with ValueError: {e}")
    
    # STEP 5: Test replay without historical policy hash (uses current)
    print("\n--- STEP 5: Test Replay Without Historical Policy Hash ---")
    print("Replay without historical_policy_hash should use current policy")
    
    replay_current = engine_v2.evaluate_decision(input_event, replay_mode=False)
    replay_current_decision = replay_current["decision"]
    
    print(f"Replay without historical hash: {replay_current_decision}")
    assert replay_current_decision != original_decision, \
        "Replay without historical hash should use current policy (different decision)"
    print(f"[PASS] Replay without historical hash uses current policy ({replay_current_decision})")
    
    print("\n" + "="*60)
    print("HISTORICAL POLICY BINDING TEST: PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Replay decision matches original decision")
    print("  [PASS] Replay uses historical policy hash")
    print("  [PASS] Replay uses historical policy version")
    print("  [PASS] Replay does NOT use current policy")
    print("  [PASS] Replay fails when historical policy not found")
    print("  [PASS] Replay without historical hash uses current policy")
    print("\nConclusion:")
    print("  Historical policy binding is enforced")
    print("  Replay never silently substitutes current policy")
    print("  Replay time lock is functional")


if __name__ == "__main__":
    test_historical_policy_binding()
