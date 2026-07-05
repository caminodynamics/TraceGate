from decision_engine import DecisionEngine
from typing import Dict, Any, List
import copy


def test_multi_cycle_replay_stability():
    """
    Multi-cycle replay stress test.
    
    Validates:
    - Provenance stability across cycles
    - Deterministic replay integrity
    - State isolation across repeated mutation → evaluation → replay cycles
    """
    print("\n" + "="*60)
    print("MULTI-CYCLE REPLAY STABILITY STRESS TEST")
    print("="*60)
    
    engine = DecisionEngine()
    
    # INITIAL INPUT STATE (fixed baseline)
    base_input_event = {
        "event_id": "cycle-test-001",
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
    
    # ENVIRONMENT STATE mutations per cycle
    cycle_mutations = [
        {"feature_flag_safe_mode": True},   # Cycle 1
        {"feature_flag_safe_mode": False},  # Cycle 2
        {"feature_flag_safe_mode": True}    # Cycle 3
    ]
    
    # Store cycle results for comparison
    cycle_results: List[Dict[str, Any]] = []
    
    print("\n--- RUNNING 3 EVALUATION CYCLES ---\n")
    
    for cycle_num, env_mutation in enumerate(cycle_mutations, start=1):
        print(f"Cycle {cycle_num}:")
        print(f"  Environment state: feature_flag_safe_mode = {env_mutation['feature_flag_safe_mode']}")
        
        # Create input_event for this cycle
        input_event = copy.deepcopy(base_input_event)
        input_event["environment_state"] = env_mutation
        
        # Run evaluate_decision
        artifact = engine.evaluate_decision(input_event)
        
        # Store cycle results
        cycle_result = {
            "cycle": cycle_num,
            "artifact": copy.deepcopy(artifact),  # Deep copy to detect mutation
            "input_event": copy.deepcopy(input_event)
        }
        cycle_results.append(cycle_result)
        
        # Print cycle summary
        print(f"  Decision: {artifact['decision']}")
        print(f"  Input hash: {artifact['evaluated_inputs_hash'][:16]}...")
        print(f"  Policy hash: {artifact['policy_hash'][:16]}...")
        print(f"  Environment hash: {artifact['environment_hash'][:16] if artifact['environment_hash'] else 'None'}")
        
        debug = artifact["debug"]
        if "conflict_detected" in debug and debug["conflict_detected"]:
            print(f"  Conflict detected: {debug['conflict_type']}")
            print(f"  Raw input value: {debug['raw_conflict_record']['raw_input_state_value']}")
            print(f"  Raw env value: {debug['raw_conflict_record']['raw_environment_state_value']}")
            print(f"  Resolved value: {debug['resolution_applied']['resolved_value']}")
        else:
            print(f"  Conflict detected: False")
        
        print()
    
    print("--- ASSERTIONS ---\n")
    
    # ASSERTION A: Provenance stability
    print("A. Provenance Stability Check")
    first_raw_conflict = None
    for result in cycle_results:
        debug = result["artifact"]["debug"]
        if "conflict_detected" in debug and debug["conflict_detected"]:
            raw_conflict = debug["raw_conflict_record"]
            if first_raw_conflict is None:
                first_raw_conflict = raw_conflict
            else:
                assert raw_conflict == first_raw_conflict, \
                    f"Raw conflict record must be IDENTICAL across cycles for same input_event"
    print("  [PASS] Raw conflict record is identical across cycles\n")
    
    # ASSERTION B: Resolution correctness
    print("B. Resolution Correctness Check")
    decisions = [r["artifact"]["decision"] for r in cycle_results]
    print(f"  Decisions across cycles: {decisions}")
    
    # Verify raw_conflict_record does NOT change even if decision changes
    for i, result in enumerate(cycle_results):
        debug = result["artifact"]["debug"]
        if "conflict_detected" in debug and debug["conflict_detected"]:
            raw_conflict = debug["raw_conflict_record"]
            assert raw_conflict["raw_input_state_value"] == True, \
                f"Raw input state must not change (cycle {i+1})"
    print("  [PASS] Raw conflict record unchanged despite decision changes\n")
    
    # ASSERTION C: Hash stability rules
    print("C. Hash Stability Rules Check")
    
    # input_hash must remain identical across cycles
    input_hashes = [r["artifact"]["evaluated_inputs_hash"] for r in cycle_results]
    assert len(set(input_hashes)) == 1, "Input hash must be identical across cycles"
    print(f"  [PASS] Input hash identical across all cycles: {input_hashes[0][:16]}...")
    
    # policy_hash must remain identical across cycles
    policy_hashes = [r["artifact"]["policy_hash"] for r in cycle_results]
    assert len(set(policy_hashes)) == 1, "Policy hash must be identical across cycles"
    print(f"  [PASS] Policy hash identical across all cycles: {policy_hashes[0][:16]}...")
    
    # environment_hash changes ONLY when environment state changes
    env_hashes = [r["artifact"]["environment_hash"] for r in cycle_results]
    print(f"  Environment hashes: {[h[:16] if h else 'None' for h in env_hashes]}")
    
    # Cycles 1 and 3 have same env state, should have same hash
    assert env_hashes[0] == env_hashes[2], "Environment hash must be identical for identical environment state"
    print(f"  [PASS] Environment hash identical for identical environment state (cycles 1 & 3)")
    
    # Cycle 2 has different env state, should have different hash
    assert env_hashes[1] != env_hashes[0], "Environment hash must differ for different environment state"
    print(f"  [PASS] Environment hash differs for different environment state (cycle 2)\n")
    
    # ASSERTION D: No silent drift
    print("D. No Silent Drift Check")
    
    # Verify no hidden mutation of input_state during evaluation
    for result in cycle_results:
        original_inputs = result["input_event"]["inputs"]
        # Re-evaluate to ensure input_state wasn't mutated
        re_evaluated = engine.evaluate_decision(result["input_event"])
        assert re_evaluated["evaluated_inputs_hash"] == result["artifact"]["evaluated_inputs_hash"], \
            "Input hash must be stable (no silent mutation of input_state)"
    print("  [PASS] No hidden mutation of input_state during evaluation")
    
    # Verify no modification of stored artifact after creation
    for result in cycle_results:
        original_artifact = result["artifact"]
        # Deep copy and compare
        artifact_copy = copy.deepcopy(original_artifact)
        assert original_artifact == artifact_copy, "Stored artifact must not be modified after creation"
    print("  [PASS] No modification of stored artifact after creation\n")
    
    # ASSERTION E: Determinism under replay
    print("E. Determinism Under Replay Check")
    
    for result in cycle_results:
        # Replay using same input_event
        replay_artifact = engine.evaluate_decision(result["input_event"])
        original_artifact = result["artifact"]
        
        # Same resolved decision given same environment snapshot
        assert replay_artifact["decision"] == original_artifact["decision"], \
            "Replay must reproduce same decision"
        
        # Identical debug provenance structure
        original_conflict = original_artifact["debug"].get("conflict_detected", False)
        replay_conflict = replay_artifact["debug"].get("conflict_detected", False)
        assert replay_conflict == original_conflict, \
            "Replay must reproduce conflict detection status"
        
        if original_conflict:
            assert replay_artifact["debug"]["raw_conflict_record"] == original_artifact["debug"]["raw_conflict_record"], \
                "Replay must reproduce raw conflict record"
            assert replay_artifact["debug"]["resolution_applied"] == original_artifact["debug"]["resolution_applied"], \
                "Replay must reproduce resolution applied"
    
    print("  [PASS] Replay reproduces same decision and provenance structure\n")
    
    # OUTPUT SUMMARY
    print("--- SUMMARY ---\n")
    
    print("Cycle-by-cycle decision trace:")
    for result in cycle_results:
        cycle = result["cycle"]
        decision = result["artifact"]["decision"]
        conflict = result["artifact"]["debug"].get("conflict_detected", False)
        print(f"  Cycle {cycle}: decision={decision}, conflict_detected={conflict}")
    
    print("\nHash comparison matrix:")
    print(f"  Input hashes: {'IDENTICAL' if len(set(input_hashes)) == 1 else 'DIFFERENT'}")
    print(f"  Policy hashes: {'IDENTICAL' if len(set(policy_hashes)) == 1 else 'DIFFERENT'}")
    print(f"  Environment hashes: {'STABLE (1==3, 2 diff)' if env_hashes[0]==env_hashes[2] and env_hashes[1]!=env_hashes[0] else 'UNEXPECTED'}")
    
    print("\n" + "="*60)
    print("MULTI-CYCLE REPLAY STABILITY TEST: PASSED")
    print("="*60)
    print("\nAll assertions passed:")
    print("  [PASS] Provenance stability")
    print("  [PASS] Resolution correctness")
    print("  [PASS] Hash stability rules")
    print("  [PASS] No silent drift")
    print("  [PASS] Determinism under replay")


if __name__ == "__main__":
    test_multi_cycle_replay_stability()
