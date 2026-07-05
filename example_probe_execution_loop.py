"""
Example Probe Execution Loop - Demonstrates deterministic fault-line testing

This example demonstrates:
1. Initial probe batch execution
2. Drift detection
3. Mutated probe generation
4. Execution loop with one iteration

Note: This requires TRAXES binary to be built first:
  cd /workspace/traxes && cargo build --release
"""
from probe_execution_loop import ProbeExecutionLoop
import json


def create_sample_probes() -> list:
    """
    Create sample probes for testing.
    
    These probes represent typical TRAXES evaluation inputs.
    """
    probes = [
        {
            "tool": "AWS_RDS_PROVISION",
            "environment": "staging",
            "parameters": {
                "instance_type": "t3.micro",
                "instance_cost_per_hour": 0.015
            },
            "policy_bundle": "infra-cost-limit-v1"
        },
        {
            "tool": "AWS_RDS_PROVISION",
            "environment": "production",
            "parameters": {
                "instance_type": "m5.large",
                "instance_cost_per_hour": 0.52
            },
            "policy_bundle": "infra-cost-limit-v1"
        },
        {
            "tool": "AWS_S3_CREATE_BUCKET",
            "environment": "staging",
            "parameters": {
                "bucket_name": "test-bucket-123",
                "region": "us-east-1"
            },
            "policy_bundle": "s3-guards-v2"
        }
    ]
    
    return probes


def create_mock_drift_scenario():
    """
    Create a mock drift scenario for demonstration when TRAXES binary is not available.
    
    This simulates what would happen if TRAXES returned different results on replay.
    """
    from drift_detector import DriftDetector, DriftType
    from probe_runner import ProbeResult
    
    # Create mock evaluate artifact
    evaluate_artifact = {
        "decision": "ALLOW",
        "decision_id": "dec_abc123",
        "policy_hash": "hash1234567890",
        "policy_version": "v1.0.0",
        "timestamp": "2026-01-01T00:00:00Z",
        "sha256_hash": "sha256_abc123",
        "proposed_action": {
            "tool": "AWS_RDS_PROVISION",
            "environment": "staging",
            "parameters": {
                "instance_type": "t3.micro",
                "instance_cost_per_hour": 0.015
            }
        }
    }
    
    # Create mock replay artifact with drift
    replay_artifact = {
        "decision": "DENY",  # Decision drift
        "decision_id": "dec_xyz789",  # Decision ID drift
        "policy_hash": "hash0987654321",  # Policy hash drift
        "policy_version": "v2.0.0",  # Policy version drift
        "timestamp": "2026-01-01T00:01:00Z",  # Timestamp drift
        "sha256_hash": "sha256_xyz789",
        "proposed_action": {
            "tool": "AWS_RDS_PROVISION",
            "environment": "staging",
            "parameters": {
                "instance_type": "t3.micro",
                "instance_cost_per_hour": 0.015
            }
        }
    }
    
    return evaluate_artifact, replay_artifact


def example_with_real_traxes():
    """
    Example: Run probe execution loop with real TRAXES binary.
    """
    print("\n" + "="*60)
    print("EXAMPLE: Probe Execution Loop with Real TRAXES")
    print("="*60)
    
    # Create sample probes
    probes = create_sample_probes()
    
    print(f"\nSample probes ({len(probes)}):")
    for i, probe in enumerate(probes, 1):
        print(f"\nProbe {i}:")
        print(json.dumps(probe, indent=2))
    
    # Initialize execution loop
    loop = ProbeExecutionLoop()
    
    # Check if TRAXES is available
    if not loop.probe_runner.adapter.is_available():
        print(f"\nTRAXES binary not available at {loop.probe_runner.adapter.get_traxes_path()}")
        print("Build TRAXES with: cd /workspace/traxes && cargo build --release")
        print("\nFalling back to mock demonstration...")
        return False
    
    # Run execution loop
    summary = loop.run(probes, max_iterations=1)
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(json.dumps(summary, indent=2))
    
    # Print drift events
    drift_events = loop.get_drift_events()
    print(f"\n{'='*60}")
    print(f"DRIFT EVENTS ({len(drift_events)})")
    print(f"{'='*60}")
    
    for event in drift_events:
        print(f"\nDrift Type: {event.drift_type.value}")
        print(f"Differences: {json.dumps(event.differences, indent=2)}")
    
    # Print generated probes
    generated_probes = loop.get_generated_probes()
    print(f"\n{'='*60}")
    print(f"GENERATED PROBES ({len(generated_probes)})")
    print(f"{'='*60}")
    
    for i, probe in enumerate(generated_probes, 1):
        print(f"\nGenerated Probe {i}:")
        print(json.dumps(probe, indent=2))
    
    return True


def example_mock_demonstration():
    """
    Example: Demonstrate drift detection and probe generation with mock data.
    """
    print("\n" + "="*60)
    print("EXAMPLE: Mock Drift Detection and Probe Generation")
    print("="*60)
    
    # Create mock drift scenario
    evaluate_artifact, replay_artifact = create_mock_drift_scenario()
    
    print(f"\nMock Evaluate Artifact:")
    print(json.dumps(evaluate_artifact, indent=2))
    
    print(f"\nMock Replay Artifact (with drift):")
    print(json.dumps(replay_artifact, indent=2))
    
    # Detect drift
    from drift_detector import DriftDetector
    detector = DriftDetector()
    
    drift_event = detector.compare(evaluate_artifact, replay_artifact)
    
    if drift_event:
        print(f"\n{'='*60}")
        print("DRIFT DETECTED")
        print(f"{'='*60}")
        print(f"Drift Type: {drift_event.drift_type.value}")
        print(f"\nDifferences:")
        print(json.dumps(drift_event.differences, indent=2))
        
        # Log drift event
        log = detector.log_drift_event(drift_event)
        print(f"\nDrift Log:")
        print(log)
        
        # Generate mutated probes
        from probe_generator import ProbeGenerator
        generator = ProbeGenerator()
        
        generated_probes = generator.generate_probes(drift_event, count=3)
        
        print(f"\n{'='*60}")
        print(f"GENERATED MUTATED PROBES ({len(generated_probes)})")
        print(f"{'='*60}")
        
        for i, probe in enumerate(generated_probes, 1):
            print(f"\nMutated Probe {i}:")
            print(json.dumps(probe, indent=2))
    else:
        print("\nNo drift detected")


def example_drift_classification():
    """
    Example: Demonstrate different drift types.
    """
    print("\n" + "="*60)
    print("EXAMPLE: Drift Classification")
    print("="*60)
    
    from drift_detector import DriftDetector, DriftType
    
    detector = DriftDetector()
    
    # Test 1: Semantic drift (decision change)
    print("\n--- Test 1: Semantic Drift ---")
    eval1 = {"decision": "ALLOW", "policy_hash": "hash1"}
    replay1 = {"decision": "DENY", "policy_hash": "hash1"}
    drift1 = detector.compare(eval1, replay1)
    if drift1:
        print(f"Detected: {drift1.drift_type.value}")
        print(f"Differences: {drift1.differences}")
    
    # Test 2: Temporal drift (timestamp change)
    print("\n--- Test 2: Temporal Drift ---")
    eval2 = {"decision": "ALLOW", "timestamp": "2026-01-01T00:00:00Z"}
    replay2 = {"decision": "ALLOW", "timestamp": "2026-01-01T00:01:00Z"}
    drift2 = detector.compare(eval2, replay2)
    if drift2:
        print(f"Detected: {drift2.drift_type.value}")
        print(f"Differences: {drift2.differences}")
    
    # Test 3: Artifact drift (hash change)
    print("\n--- Test 3: Artifact Drift ---")
    eval3 = {"decision": "ALLOW", "policy_hash": "hash1", "sha256_hash": "sha1"}
    replay3 = {"decision": "ALLOW", "policy_hash": "hash2", "sha256_hash": "sha2"}
    drift3 = detector.compare(eval3, replay3)
    if drift3:
        print(f"Detected: {drift3.drift_type.value}")
        print(f"Differences: {drift3.differences}")
    
    # Test 4: No drift
    print("\n--- Test 4: No Drift ---")
    eval4 = {"decision": "ALLOW", "policy_hash": "hash1"}
    replay4 = {"decision": "ALLOW", "policy_hash": "hash1"}
    drift4 = detector.compare(eval4, replay4)
    if drift4:
        print(f"Detected: {drift4.drift_type.value}")
    else:
        print("No drift detected")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROBE EXECUTION LOOP EXAMPLES")
    print("="*60)
    
    # Try real TRAXES first
    real_traxes_success = example_with_real_traxes()
    
    if not real_traxes_success:
        # Fall back to mock demonstration
        example_mock_demonstration()
    
    # Demonstrate drift classification
    example_drift_classification()
    
    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)
