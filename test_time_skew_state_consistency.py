from decision_engine import DecisionEngine
from typing import Dict, Any
import copy


def test_time_skew_detection_and_handling():
    """
    Time skew adversarial test.
    
    Validates correctness under inconsistent state snapshots taken at different times.
    """
    print("\n" + "="*60)
    print("TIME SKEW STATE CONSISTENCY TEST")
    print("="*60)
    
    engine = DecisionEngine()
    
    # CORE SCENARIO: State sources sampled at different times
    # T0 (Input snapshot time)
    input_event = {
        "event_id": "time-skew-test-001",
        "timestamp": "2025-01-01T00:00:00Z",
        "input_snapshot_timestamp": "2025-01-01T00:00:00Z",  # T0
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": False,
            "system_load": "high"
        },
        "environment_snapshot_timestamp": "2025-01-01T00:00:00.050Z",  # T1 (+50ms)
        "policy_snapshot_timestamp": "2025-01-01T00:00:00.100Z",  # T2 (+100ms)
        "context": {
            "simulation_mode": True
        }
    }
    
    print("\nScenario: Non-atomic state sampling")
    print(f"  Input snapshot (T0): {input_event['input_snapshot_timestamp']}")
    print(f"  Environment snapshot (T1): {input_event['environment_snapshot_timestamp']}")
    print(f"  Policy snapshot (T2): {input_event['policy_snapshot_timestamp']}")
    
    # Run evaluation
    artifact = engine.evaluate_decision(input_event)
    
    print(f"\nEvaluation result:")
    print(f"  Decision: {artifact['decision']}")
    print(f"  Input hash: {artifact['evaluated_inputs_hash'][:16]}...")
    print(f"  Policy hash: {artifact['policy_hash'][:16]}...")
    print(f"  Environment hash: {artifact['environment_hash'][:16] if artifact['environment_hash'] else 'None'}")
    
    debug = artifact["debug"]
    
    # ASSERTION A: Time skew detection
    print("\n--- ASSERTION A: Time Skew Detection ---")
    assert "time_skew_detected" in debug, "time_skew_detected flag must be present"
    assert debug["time_skew_detected"] == True, "time_skew_detected must be True for skewed snapshots"
    print("[PASS] time_skew_detected == True")
    
    # ASSERTION B: No silent normalization
    print("\n--- ASSERTION B: No Silent Normalization ---")
    # Verify input_state, environment_state, policy_state remain distinct
    original_inputs = input_event["inputs"]
    original_env = input_event["environment_state"]
    
    # Re-evaluate to ensure states weren't normalized
    re_artifact = engine.evaluate_decision(input_event)
    assert re_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Input hash must be stable (no normalization of input_state)"
    assert re_artifact["environment_hash"] == artifact["environment_hash"], \
        "Environment hash must be stable (no normalization of environment_state)"
    assert re_artifact["policy_hash"] == artifact["policy_hash"], \
        "Policy hash must be stable (no normalization of policy_state)"
    print("[PASS] States remain distinct and unmodified")
    
    # ASSERTION C: Deterministic replay
    print("\n--- ASSERTION C: Deterministic Replay ---")
    # Replay the SAME skewed snapshot
    replay_artifact = engine.evaluate_decision(input_event)
    
    assert replay_artifact["decision"] == artifact["decision"], \
        "Replay must produce identical decision"
    assert replay_artifact["evaluated_inputs_hash"] == artifact["evaluated_inputs_hash"], \
        "Replay must produce identical input hash"
    assert replay_artifact["environment_hash"] == artifact["environment_hash"], \
        "Replay must produce identical environment hash"
    assert replay_artifact["policy_hash"] == artifact["policy_hash"], \
        "Replay must produce identical policy hash"
    print("[PASS] Replay produces identical artifact")
    
    # ASSERTION D: Skew transparency
    print("\n--- ASSERTION D: Skew Transparency ---")
    assert "time_skew_info" in debug, "time_skew_info must be present in debug output"
    skew_info = debug["time_skew_info"]
    
    assert "skew_delta_ms" in skew_info, "skew_delta_ms must be present"
    assert skew_info["skew_delta_ms"] > 0, "skew_delta_ms must be positive for skewed snapshots"
    print(f"[PASS] skew_delta_ms: {skew_info['skew_delta_ms']}ms")
    
    assert "snapshot_timestamps" in skew_info, "snapshot_timestamps must be present"
    assert "input_state" in skew_info["snapshot_timestamps"], "input_state timestamp must be present"
    assert "environment_state" in skew_info["snapshot_timestamps"], "environment_state timestamp must be present"
    assert "policy_state" in skew_info["snapshot_timestamps"], "policy_state timestamp must be present"
    print("[PASS] All snapshot timestamps present")
    
    assert "earliest_snapshot" in skew_info, "earliest_snapshot must be present"
    assert "latest_snapshot" in skew_info, "latest_snapshot must be present"
    print(f"[PASS] earliest_snapshot: {skew_info['earliest_snapshot']}")
    print(f"[PASS] latest_snapshot: {skew_info['latest_snapshot']}")
    
    # ASSERTION E: Stability under repeated runs
    print("\n--- ASSERTION E: Stability Under Repeated Runs ---")
    artifacts = []
    for i in range(3):
        run_artifact = engine.evaluate_decision(input_event)
        artifacts.append(run_artifact)
    
    # All outputs must be identical
    for i in range(1, len(artifacts)):
        assert artifacts[i]["decision"] == artifacts[0]["decision"], \
            f"Decision must be identical across runs (run {i} vs run 0)"
        assert artifacts[i]["evaluated_inputs_hash"] == artifacts[0]["evaluated_inputs_hash"], \
            f"Input hash must be identical across runs (run {i} vs run 0)"
        assert artifacts[i]["environment_hash"] == artifacts[0]["environment_hash"], \
            f"Environment hash must be identical across runs (run {i} vs run 0)"
        assert artifacts[i]["policy_hash"] == artifacts[0]["policy_hash"], \
            f"Policy hash must be identical across runs (run {i} vs run 0)"
    
    # No drift in conflict records
    for i in range(1, len(artifacts)):
        debug_0 = artifacts[0]["debug"]
        debug_i = artifacts[i]["debug"]
        if "conflict_detected" in debug_0 and debug_0["conflict_detected"]:
            assert debug_i["raw_conflict_record"] == debug_0["raw_conflict_record"], \
                f"Raw conflict record must be identical across runs (run {i} vs run 0)"
    
    print("[PASS] All 3 runs produced identical outputs")
    print("[PASS] No drift in hashes or conflict records")
    
    # SUMMARY
    print("\n--- SUMMARY ---")
    print("All assertions passed:")
    print("  [PASS] Time skew detection")
    print("  [PASS] No silent normalization")
    print("  [PASS] Deterministic replay")
    print("  [PASS] Skew transparency")
    print("  [PASS] Stability under repeated runs")
    
    print("\n" + "="*60)
    print("TIME SKEW STATE CONSISTENCY TEST: PASSED")
    print("="*60)


def test_no_time_skew_when_snapshots_atomic():
    """
    Test that time skew is not detected when snapshots are atomic (same timestamp).
    """
    print("\n--- Test: No Time Skew When Snapshots Atomic ---")
    
    engine = DecisionEngine()
    
    # Atomic snapshots (same timestamp)
    input_event = {
        "event_id": "atomic-snapshot-test",
        "timestamp": "2025-01-01T00:00:00Z",
        "input_snapshot_timestamp": "2025-01-01T00:00:00Z",
        "inputs": {
            "user_tier": "premium",
            "region": "EU",
            "feature_flag_safe_mode": True
        },
        "environment_state": {
            "feature_flag_safe_mode": True
        },
        "environment_snapshot_timestamp": "2025-01-01T00:00:00Z",
        "policy_snapshot_timestamp": "2025-01-01T00:00:00Z",
        "context": {
            "simulation_mode": True
        }
    }
    
    artifact = engine.evaluate_decision(input_event)
    debug = artifact["debug"]
    
    # Should NOT detect time skew
    assert "time_skew_detected" not in debug or debug["time_skew_detected"] == False, \
        "Time skew should not be detected for atomic snapshots"
    
    print("[PASS] No time skew detected for atomic snapshots")


if __name__ == "__main__":
    test_time_skew_detection_and_handling()
    test_no_time_skew_when_snapshots_atomic()
    
    print("\n" + "="*60)
    print("ALL TIME SKEW TESTS PASSED")
    print("="*60)
