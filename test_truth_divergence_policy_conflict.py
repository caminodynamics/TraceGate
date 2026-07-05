from decision_engine import DecisionEngine
from typing import Dict, Any


def test_truth_divergence_policy_conflict():
    """
    Truth divergence adversarial test.
    
    Validates system behavior when INTERNAL policy state conflicts with 
    an EXTERNAL authoritative policy source.
    """
    print("\n" + "="*60)
    print("TRUTH DIVERGENCE POLICY CONFLICT TEST")
    print("="*60)
    
    print("\nINTERNAL POLICY STATE (system-defined):")
    print("  IF user_tier == premium AND region == EU THEN ALLOW")
    
    print("\nEXTERNAL POLICY SOURCE (authoritative override feed):")
    print("  IF user_tier == premium AND region == EU THEN DENY")
    print("  source: compliance_override_v2")
    print("  version: 3.1")
    print("  signature: VALID_EXTERNAL_AUTHORITY")
    
    engine = DecisionEngine()
    
    # INPUT STATE
    input_event = {
        "event_id": "truth-divergence-test-001",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        # External policy (conflicts with internal)
        "external_policy": {
            "policy_source": """
            IF user_tier == "premium"
            AND region == "EU"
            THEN DENY
            ELSE ALLOW
            """,
            "source": "compliance_override_v2",
            "version": "3.1",
            "signature": "VALID_EXTERNAL_AUTHORITY"
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    print("\nINPUT STATE:")
    print("  user_tier: premium")
    print("  region: EU")
    print("  feature_flag_safe_mode: true")
    
    # Evaluate decision
    artifact = engine.evaluate_decision(input_event)
    
    print(f"\nEVALUATION RESULT:")
    print(f"  Decision: {artifact['decision']}")
    print(f"  Internal policy hash: {artifact['policy_hash'][:16]}...")
    
    debug = artifact["debug"]
    
    # ASSERTION A: Divergence detection
    print("\n--- ASSERTION A: Divergence Detection ---")
    assert "policy_divergence_report" in debug, \
        "policy_divergence_report must be present"
    
    divergence_report = debug["policy_divergence_report"]
    assert divergence_report["policy_divergence_detected"] == True, \
        "policy_divergence_detected must be True"
    print("[PASS] policy_divergence_detected == True")
    
    # ASSERTION B: Dual preservation
    print("\n--- ASSERTION B: Dual Preservation ---")
    assert "internal_policy_hash" in divergence_report, \
        "internal_policy_hash must be present"
    assert "external_policy_hash" in divergence_report, \
        "external_policy_hash must be present"
    assert divergence_report["internal_policy_hash"] != divergence_report["external_policy_hash"], \
        "Internal and external policy hashes must differ (divergence confirmed)"
    print("[PASS] Both internal and external policy snapshots exist")
    print(f"[PASS] Internal policy hash: {divergence_report['internal_policy_hash'][:16]}...")
    print(f"[PASS] External policy hash: {divergence_report['external_policy_hash'][:16]}...")
    
    # ASSERTION C: Deterministic resolution
    print("\n--- ASSERTION C: Deterministic Resolution ---")
    assert divergence_report["selected_policy_source"] == "external", \
        "selected_policy_source must be 'external' (valid signature)"
    assert divergence_report["resolution_rule_applied"] == "external_authority_override", \
        "resolution_rule_applied must be 'external_authority_override'"
    print("[PASS] selected_policy_source == external")
    print("[PASS] resolution_rule_applied == external_authority_override")
    
    # Verify repeated runs produce identical selected policy source
    artifacts = []
    for i in range(3):
        run_artifact = engine.evaluate_decision(input_event)
        artifacts.append(run_artifact)
    
    for i in range(1, len(artifacts)):
        run_divergence_report = artifacts[i]["debug"]["policy_divergence_report"]
        assert run_divergence_report["selected_policy_source"] == divergence_report["selected_policy_source"], \
            f"Selected policy source must be identical across runs (run {i} vs run 0)"
    print("[PASS] Repeated runs produce identical selected policy source")
    
    # ASSERTION D: No silent merging
    print("\n--- ASSERTION D: No Silent Merging ---")
    # System does NOT merge internal + external policy rules
    assert divergence_report["internal_policy_hash"] == artifact["policy_hash"], \
        "Internal policy hash must match computed policy hash (no merging)"
    
    # System does NOT reconcile rules heuristically
    assert divergence_report["external_policy_source"] == "compliance_override_v2", \
        "External policy source must be preserved exactly"
    assert divergence_report["external_policy_version"] == "3.1", \
        "External policy version must be preserved exactly"
    assert divergence_report["external_policy_signature"] == "VALID_EXTERNAL_AUTHORITY", \
        "External policy signature must be preserved exactly"
    print("[PASS] No silent merging of policy rules")
    print("[PASS] No heuristic reconciliation")
    
    # ASSERTION E: Provenance integrity
    print("\n--- ASSERTION E: Provenance Integrity ---")
    # All hashes remain stable across replay cycles
    replay_artifact = engine.evaluate_decision(input_event)
    assert replay_artifact["policy_hash"] == artifact["policy_hash"], \
        "Policy hash must be stable across replay"
    assert replay_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Input hash must be stable across replay"
    
    replay_divergence_report = replay_artifact["debug"]["policy_divergence_report"]
    assert replay_divergence_report["internal_policy_hash"] == divergence_report["internal_policy_hash"], \
        "Internal policy hash must be stable across replay"
    assert replay_divergence_report["external_policy_hash"] == divergence_report["external_policy_hash"], \
        "External policy hash must be stable across replay"
    print("[PASS] All hashes remain stable across replay cycles")
    
    print("\n" + "="*60)
    print("TRUTH DIVERGENCE POLICY CONFLICT TEST: PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Divergence detection")
    print("  [PASS] Dual preservation")
    print("  [PASS] Deterministic resolution")
    print("  [PASS] No silent merging")
    print("  [PASS] Provenance integrity")
    print("\nSystem detects policy divergence across sources")
    print("External policy takes precedence with valid signature")
    print("Both policies preserved in immutable provenance")


def test_policy_divergence_invalid_signature():
    """
    Test policy divergence when external signature is invalid.
    Internal policy should take precedence.
    """
    print("\n" + "="*60)
    print("POLICY DIVERGENCE - INVALID SIGNATURE TEST")
    print("="*60)
    
    engine = DecisionEngine()
    
    input_event = {
        "event_id": "divergence-invalid-sig",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "external_policy": {
            "policy_source": """
            IF user_tier == "premium"
            AND region == "EU"
            THEN DENY
            """,
            "source": "untrusted_source",
            "version": "1.0",
            "signature": "INVALID_SIGNATURE"  # Invalid signature
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    debug = artifact["debug"]
    
    assert "policy_divergence_report" in debug, \
        "policy_divergence_report must be present"
    
    divergence_report = debug["policy_divergence_report"]
    assert divergence_report["policy_divergence_detected"] == True, \
        "Divergence must be detected"
    
    # Internal policy should take precedence due to invalid signature
    assert divergence_report["selected_policy_source"] == "internal", \
        "Internal policy should take precedence with invalid signature"
    assert divergence_report["resolution_rule_applied"] == "internal_policy_default", \
        "Resolution reason should be internal_policy_default"
    
    print("[PASS] Internal policy takes precedence with invalid signature")
    print("[PASS] DIVERGENCE - INVALID SIGNATURE TEST: PASSED")


def test_no_policy_divergence_when_policies_match():
    """
    Test that no divergence is detected when policies match exactly.
    """
    print("\n" + "="*60)
    print("NO POLICY DIVERGENCE WHEN POLICIES MATCH TEST")
    print("="*60)
    
    engine = DecisionEngine()
    
    # External policy matches internal policy exactly (same source string)
    input_event = {
        "event_id": "no-divergence-test",
        "timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "external_policy": {
            # Use exact same policy source as internal policy
            "policy_source": """
        IF user_tier == "premium"
        AND region == "EU"
        AND feature_flag_safe_mode == true
        THEN ALLOW
        ELSE DENY
        """,
            "source": "matching_source",
            "version": "1.0",
            "signature": "VALID_EXTERNAL_AUTHORITY"
        },
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    debug = artifact["debug"]
    
    # No divergence should be detected - report should not be present or should indicate no divergence
    if "policy_divergence_report" in debug:
        assert debug["policy_divergence_report"]["policy_divergence_detected"] == False, \
            "No divergence should be detected when policies match exactly"
    else:
        # Report not present is also acceptable (no divergence to report)
        pass
    
    print("[PASS] No divergence detected when policies match exactly")
    print("[PASS] NO POLICY DIVERGENCE TEST: PASSED")


if __name__ == "__main__":
    test_truth_divergence_policy_conflict()
    test_policy_divergence_invalid_signature()
    test_no_policy_divergence_when_policies_match()
    
    print("\n" + "="*60)
    print("ALL TRUTH DIVERGENCE TESTS PASSED")
    print("="*60)
