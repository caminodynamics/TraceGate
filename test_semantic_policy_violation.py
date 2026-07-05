from decision_engine import DecisionEngine
from typing import Dict, Any
import json


def load_golden_policy() -> Dict[str, Any]:
    """
    Load golden policy from golden_policy.json.
    This is the ONLY source of truth for policy evaluation.
    """
    with open("golden_policy.json", "r") as f:
        return json.load(f)


def golden_oracle_decision(inputs: Dict[str, Any]) -> str:
    """
    GOLDEN POLICY ORACLE (GROUND TRUTH)
    
    This oracle uses golden_policy.json as the ONLY source of truth.
    Any mismatch between engine output and golden_policy.json is a HARD FAILURE.
    """
    policy = load_golden_policy()
    
    for rule in policy["rules"]:
        condition = rule["condition"]
        decision = rule["decision"]
        
        # Evaluate condition against inputs
        # Parse simple conditions: user_tier == 'premium' AND region == 'EU' AND feature_flag_safe_mode == true
        conditions = [c.strip() for c in condition.split("AND")]
        
        all_match = True
        for cond in conditions:
            if "user_tier" in cond:
                expected = cond.split("'")[1] if "'" in cond else cond.split()[-1]
                if inputs.get("user_tier") != expected:
                    all_match = False
                    break
            elif "region" in cond:
                expected = cond.split("'")[1] if "'" in cond else cond.split()[-1]
                if inputs.get("region") != expected:
                    all_match = False
                    break
            elif "feature_flag_safe_mode" in cond:
                expected = cond.split()[-1]
                if str(inputs.get("feature_flag_safe_mode")).lower() != expected.lower():
                    all_match = False
                    break
        
        if all_match:
            return decision
    
    # Default: ALLOW if no rules match (blacklist approach per golden_policy.json)
    return "ALLOW"


def test_semantic_policy_correctness():
    """
    Semantic policy violation test.
    
    Validates whether engine output matches golden_policy.json.
    This test ensures the engine's output matches the golden policy.
    Any mismatch is a HARD FAILURE.
    """
    print("\n" + "="*60)
    print("SEMANTIC POLICY VIOLATION TEST")
    print("="*60)
    
    golden_policy = load_golden_policy()
    print("\nGOLDEN POLICY (golden_policy.json - ONLY SOURCE OF TRUTH):")
    for rule in golden_policy["rules"]:
        print(f"  Rule: {rule['name']}")
        print(f"  Condition: {rule['condition']}")
        print(f"  Decision: {rule['decision']}")
    
    print("\nENGINE POLICY (as implemented):")
    print("  DENY if user_tier == 'premium' AND region == 'EU' AND safe_mode == true")
    print("  ALLOW otherwise")
    
    engine = DecisionEngine()
    
    # INPUT STATE (fully valid and complete)
    input_event = {
        "event_id": "semantic-test-001",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": True,
            "system_load": "normal"
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("\nINPUT STATE:")
    print("  user_tier: premium")
    print("  region: EU")
    print("  feature_flag_safe_mode: true")
    
    print("\nENVIRONMENT STATE:")
    print("  feature_flag_safe_mode: true")
    print("  system_load: normal")
    
    # Evaluate decision
    artifact = engine.evaluate_decision(input_event)
    
    # Evaluate with golden policy oracle
    golden_decision = golden_oracle_decision(input_event["inputs"])
    
    print(f"\nEVALUATION RESULT:")
    print(f"  Engine decision: {artifact['decision']}")
    print(f"  Golden policy decision: {golden_decision}")
    print(f"  Input hash: {artifact['evaluated_inputs_hash'][:16]}...")
    print(f"  Policy hash: {artifact['policy_hash'][:16]}...")
    print(f"  Environment hash: {artifact['environment_hash'][:16] if artifact['environment_hash'] else 'None'}")
    
    debug = artifact["debug"]
    print(f"  Reason: {debug['reason']}")
    print(f"  Matched rules: {debug['matched_rules']}")
    
    # ASSERTION A: Semantic correctness (per golden policy)
    print("\n--- ASSERTION A: Semantic Correctness (per golden_policy.json) ---")
    # According to golden_policy.json, premium + EU + safe_mode=true should be DENY
    expected_decision = golden_decision
    assert artifact["decision"] == expected_decision, \
        f"Decision must be {expected_decision} per golden_policy.json, got {artifact['decision']}"
    print(f"[PASS] Decision == {expected_decision} (golden policy enforced correctly)")
    
    # ASSERTION B: Provenance still correct
    print("\n--- ASSERTION B: Provenance Correctness ---")
    # Raw input_state is unchanged
    original_inputs = input_event["inputs"]
    re_artifact = engine.evaluate_decision(input_event)
    assert re_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Input hash must be stable (raw input_state unchanged)"
    print("[PASS] Raw input_state unchanged")
    
    # Policy state is unchanged
    assert re_artifact["policy_hash"] == artifact["policy_hash"], \
        "Policy hash must be stable (policy_state unchanged)"
    print("[PASS] Policy state unchanged")
    
    # Environment state is unchanged
    assert re_artifact["environment_hash"] == artifact["environment_hash"], \
        "Environment hash must be stable (environment_state unchanged)"
    print("[PASS] Environment state unchanged")
    
    # ASSERTION C: Hash correctness
    print("\n--- ASSERTION C: Hash Correctness ---")
    # Input hash should be stable and correct
    assert artifact["evaluated_inputs_hash"] is not None, \
        "Input hash must be computed"
    assert len(artifact["evaluated_inputs_hash"]) == 64, \
        "Input hash must be SHA256 (64 hex chars)"
    print("[PASS] Input hash stable and correct")
    
    # Policy hash should be stable and correct
    assert artifact["policy_hash"] is not None, \
        "Policy hash must be computed"
    assert len(artifact["policy_hash"]) == 64, \
        "Policy hash must be SHA256 (64 hex chars)"
    print("[PASS] Policy hash stable and correct")
    
    # Environment hash should be stable and correct
    assert artifact["environment_hash"] is not None, \
        "Environment hash must be computed"
    assert len(artifact["environment_hash"]) == 64, \
        "Environment hash must be SHA256 (64 hex chars)"
    print("[PASS] Environment hash stable and correct")
    
    # ASSERTION D: No silent normalization
    print("\n--- ASSERTION D: No Silent Normalization ---")
    # System does NOT reinterpret or "optimize away" policy semantics
    # Verify the decision is based on exact policy evaluation, not shortcuts
    assert debug["matched_rules"] == ["user_tier == premium", "region == EU", "feature_flag_safe_mode == true"], \
        "Matched rules must reflect exact policy conditions"
    print("[PASS] No silent normalization or policy simplification")
    
    # ASSERTION E: Explicit reasoning trace exists
    print("\n--- ASSERTION E: Explicit Reasoning Trace ---")
    # Artifact includes explicit reason and matched rules
    assert "reason" in debug, "Artifact must include reason field"
    assert debug["reason"] == "Premium EU users denied per compliance rule", \
        "Reason must explicitly state policy conditions"
    assert "matched_rules" in debug, "Artifact must include matched_rules field"
    assert len(debug["matched_rules"]) > 0, "Matched rules must be non-empty for DENY decision"
    print("[PASS] Explicit reasoning trace exists")
    print(f"  Reason: {debug['reason']}")
    print(f"  Matched rules: {debug['matched_rules']}")
    
    # Test with ALLOW scenario to validate semantic correctness in both directions
    print("\n--- VALIDATING ALLOW SCENARIO ---")
    allow_input_event = {
        "event_id": "semantic-test-002",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "standard",  # Not premium
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
    
    allow_artifact = engine.evaluate_decision(allow_input_event)
    allow_golden_decision = golden_oracle_decision(allow_input_event["inputs"])
    assert allow_artifact["decision"] == allow_golden_decision, \
        f"Decision must be {allow_golden_decision} per golden_policy.json, got {allow_artifact['decision']}"
    print(f"[PASS] ALLOW scenario: semantic correctness holds (per golden_policy.json)")
    
    print("\n" + "="*60)
    print("SEMANTIC POLICY VIOLATION TEST: PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Semantic correctness (per golden_policy.json)")
    print("  [PASS] Provenance correctness")
    print("  [PASS] Hash correctness")
    print("  [PASS] No silent normalization")
    print("  [PASS] Explicit reasoning trace")
    print("\nEngine enforces policy meaning correctly per golden_policy.json")


def test_policy_semantic_edge_cases():
    """
    Test edge cases for semantic policy correctness.
    """
    print("\n" + "="*60)
    print("SEMANTIC POLICY EDGE CASES TEST")
    print("="*60)
    
    engine = DecisionEngine()
    
    # Edge case 1: All conditions met except one
    print("\nEdge Case 1: All conditions met except region")
    input_event = {
        "event_id": "edge-case-1",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "US",  # Not EU
            "feature_flag_safe_mode": True
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    golden_decision = golden_oracle_decision(input_event["inputs"])
    assert artifact["decision"] == golden_decision, \
        f"Decision must be {golden_decision} per golden_policy.json, got {artifact['decision']}"
    print(f"[PASS] Edge case 1: {golden_decision} (region != EU)")
    
    # Edge case 2: All conditions met except feature flag
    print("\nEdge Case 2: All conditions met except feature flag")
    input_event = {
        "event_id": "edge-case-2",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": False  # Not true
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    golden_decision = golden_oracle_decision(input_event["inputs"])
    assert artifact["decision"] == golden_decision, \
        f"Decision must be {golden_decision} per golden_policy.json, got {artifact['decision']}"
    print(f"[PASS] Edge case 2: {golden_decision} (feature_flag != true)")
    
    # Edge case 3: None of the conditions met
    print("\nEdge Case 3: None of the conditions met")
    input_event = {
        "event_id": "edge-case-3",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "standard",
            "region": "US",
            "feature_flag_safe_mode": False
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    golden_decision = golden_oracle_decision(input_event["inputs"])
    assert artifact["decision"] == golden_decision, \
        f"Decision must be {golden_decision} per golden_policy.json, got {artifact['decision']}"
    print(f"[PASS] Edge case 3: {golden_decision} (no conditions met)")
    
    print("\n" + "="*60)
    print("SEMANTIC POLICY EDGE CASES TEST: PASSED")
    print("="*60)


if __name__ == "__main__":
    test_semantic_policy_correctness()
    test_policy_semantic_edge_cases()
    
    print("\n" + "="*60)
    print("ALL SEMANTIC POLICY TESTS PASSED")
    print("="*60)
