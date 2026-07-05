"""
Example TRAXES Integration - Evaluate/Replay Roundtrip

This example demonstrates how to use the TraxesAdapter to:
1. Evaluate an action using TRAXES binary
2. Replay the decision artifact
3. Verify deterministic behavior

Note: This requires TRAXES binary to be built first:
  cd /workspace/traxes && cargo build --release
"""
from traxes_adapter import TraxesAdapter
import json


def example_evaluate_replay_roundtrip():
    """
    Example: Evaluate an action and replay the artifact.
    """
    print("="*60)
    print("TRAXES INTEGRATION EXAMPLE: Evaluate/Replay Roundtrip")
    print("="*60)
    
    # Initialize TraxesAdapter
    print("\n1. Initialize TraxesAdapter")
    adapter = TraxesAdapter()
    
    if not adapter.is_available():
        print(f"ERROR: TRAXES binary not found at {adapter.get_traxes_path()}")
        print("Build TRAXES with: cd /workspace/traxes && cargo build --release")
        return
    
    print(f"TRAXES binary: {adapter.get_traxes_path()}")
    
    # Define input for evaluation
    print("\n2. Define action for evaluation")
    input_data = {
        "tool": "AWS_RDS_PROVISION",
        "environment": "staging",
        "parameters": {
            "instance_type": "t3.micro",
            "instance_cost_per_hour": 0.015
        },
        "policy_bundle": "infra-cost-limit-v1"
    }
    
    print("Input:")
    print(json.dumps(input_data, indent=2))
    
    # Evaluate action
    print("\n3. Evaluate action using TRAXES")
    try:
        artifact = adapter.evaluate(input_data)
        print("Evaluation successful!")
        print("\nArtifact:")
        print(json.dumps(artifact, indent=2))
        
        # Extract key fields
        decision = artifact.get("decision")
        decision_id = artifact.get("decision_id")
        policy_hash = artifact.get("policy_hash")
        
        print(f"\nKey fields:")
        print(f"  Decision: {decision}")
        print(f"  Decision ID: {decision_id}")
        print(f"  Policy Hash: {policy_hash[:16]}...")
        
    except RuntimeError as e:
        print(f"ERROR: Evaluation failed: {e}")
        return
    
    # Replay artifact
    print("\n4. Replay artifact using TRAXES")
    try:
        replay_result = adapter.replay(artifact)
        print("Replay successful!")
        print("\nReplay Result:")
        print(json.dumps(replay_result, indent=2))
        
        # Verify deterministic behavior
        print("\n5. Verify deterministic behavior")
        original_decision = artifact.get("decision")
        replay_decision = replay_result.get("replay_decision")
        decision_match = replay_result.get("decision_match", False)
        
        print(f"Original decision: {original_decision}")
        print(f"Replay decision: {replay_decision}")
        print(f"Decision match: {decision_match}")
        
        if decision_match and original_decision == replay_decision:
            print("\n✓ SUCCESS: Replay produced identical decision")
            print("✓ Deterministic behavior verified")
        else:
            print("\n✗ ERROR: Replay produced different decision")
            print("✗ Deterministic behavior violated")
            
    except RuntimeError as e:
        print(f"ERROR: Replay failed: {e}")
        return
    
    print("\n" + "="*60)
    print("EVALUATE/REPLAY ROUNDTRIP COMPLETE")
    print("="*60)


def example_multiple_evaluations():
    """
    Example: Evaluate multiple actions to demonstrate consistency.
    """
    print("\n" + "="*60)
    print("TRAXES INTEGRATION EXAMPLE: Multiple Evaluations")
    print("="*60)
    
    adapter = TraxesAdapter()
    
    if not adapter.is_available():
        print(f"ERROR: TRAXES binary not found")
        return
    
    # Define multiple inputs
    inputs = [
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
        }
    ]
    
    print(f"\nEvaluating {len(inputs)} actions...")
    
    for i, input_data in enumerate(inputs, 1):
        print(f"\n--- Action {i} ---")
        print(f"Tool: {input_data['tool']}")
        print(f"Environment: {input_data['environment']}")
        print(f"Instance Type: {input_data['parameters']['instance_type']}")
        
        try:
            artifact = adapter.evaluate(input_data)
            decision = artifact.get("decision")
            print(f"Decision: {decision}")
        except RuntimeError as e:
            print(f"ERROR: {e}")
    
    print("\n" + "="*60)
    print("MULTIPLE EVALUATIONS COMPLETE")
    print("="*60)


def example_error_handling():
    """
    Example: Demonstrate error handling for various failure modes.
    """
    print("\n" + "="*60)
    print("TRAXES INTEGRATION EXAMPLE: Error Handling")
    print("="*60)
    
    # Test with invalid binary path
    print("\n1. Test with invalid binary path")
    invalid_adapter = TraxesAdapter(traxes_binary_path="/nonexistent/traxes")
    
    if not invalid_adapter.is_available():
        print("✓ Correctly detected missing binary")
    else:
        print("✗ Failed to detect missing binary")
    
    # Test with valid adapter
    print("\n2. Test with valid adapter")
    adapter = TraxesAdapter()
    
    if adapter.is_available():
        print("✓ Binary found")
        
        # Test with invalid input
        print("\n3. Test with invalid input")
        try:
            adapter.evaluate({"invalid": "data"})
        except RuntimeError as e:
            print(f"✓ Correctly handled invalid input: {e}")
    else:
        print("Binary not available, skipping error handling tests")
    
    print("\n" + "="*60)
    print("ERROR HANDLING EXAMPLE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Run all examples
    example_evaluate_replay_roundtrip()
    example_multiple_evaluations()
    example_error_handling()
    
    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)
