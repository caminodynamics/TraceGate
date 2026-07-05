from typing import Dict, Any
import hashlib


class MutationSimulator:
    """Simulate adversarial mutations to test replay consistency."""

    @staticmethod
    def mutate_feature_flag(input_event: Dict[str, Any], new_value: bool) -> Dict[str, Any]:
        """Mutate the feature flag value in input_event."""
        mutated = input_event.copy()
        mutated["inputs"] = input_event["inputs"].copy()
        mutated["inputs"]["feature_flag_safe_mode"] = new_value
        return mutated

    @staticmethod
    def mutate_external_state(input_event: Dict[str, Any], new_region: str) -> Dict[str, Any]:
        """Mutate external state (region) in input_event."""
        mutated = input_event.copy()
        mutated["inputs"] = input_event["inputs"].copy()
        mutated["inputs"]["region"] = new_region
        return mutated

    @staticmethod
    def mutate_policy_hash_in_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate the policy hash in a stored artifact to simulate policy change."""
        mutated = artifact.copy()
        fake_hash = hashlib.sha256(b"mutated_policy").hexdigest()
        mutated["policy_hash"] = fake_hash
        mutated["determinism_flags"]["mutation_detected"] = True
        return mutated
