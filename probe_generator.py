"""
ProbeGenerator - Generates mutated probes from drift events

Deterministic, rule-based probe generation.
For each drift event, generates 1-3 mutated probes by:
- flipping input state values
- modifying policy conditions slightly
- altering temporal version references
"""
import copy
from typing import Dict, Any, List, Optional
from drift_detector import DriftEvent, DriftType


class ProbeGenerator:
    """
    Generates mutated probes from drift events.
    
    Deterministic, rule-based probe generation:
    - Flipping input state values
    - Modifying policy conditions slightly
    - Altering temporal version references
    """
    
    def __init__(self):
        self.mutation_rules = {
            "flip_boolean": self._flip_boolean,
            "invert_string": self._invert_string,
            "increment_number": self._increment_number,
            "modify_policy_version": self._modify_policy_version,
            "alter_timestamp": self._alter_timestamp
        }
    
    def generate_probes(self, drift_event: DriftEvent, count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate mutated probes from a drift event.
        
        Args:
            drift_event: DriftEvent to generate probes from
            count: Number of probes to generate (1-3)
            
        Returns:
            List of mutated probe dictionaries
        """
        original_probe = drift_event.evaluate_artifact.get("proposed_action", {})
        if not original_probe:
            # If no proposed_action, use the evaluate_artifact itself
            original_probe = drift_event.evaluate_artifact
        
        probes = []
        
        # Generate different mutations based on drift type
        if drift_event.drift_type == DriftType.SEMANTIC:
            # For semantic drift, try flipping input values
            probes.extend(self._generate_input_mutations(original_probe, count))
        elif drift_event.drift_type == DriftType.TEMPORAL:
            # For temporal drift, try modifying temporal references
            probes.extend(self._generate_temporal_mutations(original_probe, count))
        elif drift_event.drift_type == DriftType.ARTIFACT:
            # For artifact drift, try policy mutations
            probes.extend(self._generate_policy_mutations(original_probe, count))
        else:
            # For state drift, try general mutations
            probes.extend(self._generate_general_mutations(original_probe, count))
        
        return probes
    
    def _generate_input_mutations(self, probe: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Generate mutations by flipping input state values.
        """
        mutations = []
        
        # Mutation 1: Flip boolean values
        mutated_1 = copy.deepcopy(probe)
        self._apply_mutation(mutated_1, "flip_boolean")
        mutations.append(mutated_1)
        
        # Mutation 2: Invert string values
        if count >= 2:
            mutated_2 = copy.deepcopy(probe)
            self._apply_mutation(mutated_2, "invert_string")
            mutations.append(mutated_2)
        
        # Mutation 3: Increment numeric values
        if count >= 3:
            mutated_3 = copy.deepcopy(probe)
            self._apply_mutation(mutated_3, "increment_number")
            mutations.append(mutated_3)
        
        return mutations
    
    def _generate_temporal_mutations(self, probe: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Generate mutations by altering temporal references.
        """
        mutations = []
        
        # Mutation 1: Modify policy version
        mutated_1 = copy.deepcopy(probe)
        self._apply_mutation(mutated_1, "modify_policy_version")
        mutations.append(mutated_1)
        
        # Mutation 2: Alter timestamp
        if count >= 2:
            mutated_2 = copy.deepcopy(probe)
            self._apply_mutation(mutated_2, "alter_timestamp")
            mutations.append(mutated_2)
        
        # Mutation 3: Combine temporal mutations
        if count >= 3:
            mutated_3 = copy.deepcopy(probe)
            self._apply_mutation(mutated_3, "modify_policy_version")
            self._apply_mutation(mutated_3, "alter_timestamp")
            mutations.append(mutated_3)
        
        return mutations
    
    def _generate_policy_mutations(self, probe: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Generate mutations by modifying policy conditions.
        """
        mutations = []
        
        # Mutation 1: Modify policy bundle
        mutated_1 = copy.deepcopy(probe)
        if "policy_bundle" in mutated_1:
            mutated_1["policy_bundle"] = self._increment_version(mutated_1["policy_bundle"])
        mutations.append(mutated_1)
        
        # Mutation 2: Modify policy hash (if present)
        if count >= 2:
            mutated_2 = copy.deepcopy(probe)
            if "policy_hash" in mutated_2:
                mutated_2["policy_hash"] = self._flip_hash_char(mutated_2["policy_hash"])
            mutations.append(mutated_2)
        
        # Mutation 3: Combine policy mutations
        if count >= 3:
            mutated_3 = copy.deepcopy(probe)
            if "policy_bundle" in mutated_3:
                mutated_3["policy_bundle"] = self._increment_version(mutated_3["policy_bundle"])
            if "policy_hash" in mutated_3:
                mutated_3["policy_hash"] = self._flip_hash_char(mutated_3["policy_hash"])
            mutations.append(mutated_3)
        
        return mutations
    
    def _generate_general_mutations(self, probe: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Generate general mutations.
        """
        mutations = []
        
        # Mutation 1: Flip boolean
        mutated_1 = copy.deepcopy(probe)
        self._apply_mutation(mutated_1, "flip_boolean")
        mutations.append(mutated_1)
        
        # Mutation 2: Increment number
        if count >= 2:
            mutated_2 = copy.deepcopy(probe)
            self._apply_mutation(mutated_2, "increment_number")
            mutations.append(mutated_2)
        
        # Mutation 3: Invert string
        if count >= 3:
            mutated_3 = copy.deepcopy(probe)
            self._apply_mutation(mutated_3, "invert_string")
            mutations.append(mutated_3)
        
        return mutations
    
    def _apply_mutation(self, data: Dict[str, Any], mutation_type: str):
        """
        Apply a mutation rule to data recursively.
        """
        for key, value in data.items():
            if isinstance(value, dict):
                self._apply_mutation(value, mutation_type)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._apply_mutation(item, mutation_type)
            else:
                if mutation_type in self.mutation_rules:
                    data[key] = self.mutation_rules[mutation_type](value)
    
    def _flip_boolean(self, value: Any) -> Any:
        """
        Flip boolean values.
        """
        if isinstance(value, bool):
            return not value
        return value
    
    def _invert_string(self, value: Any) -> Any:
        """
        Invert string values (simple rule-based).
        """
        if isinstance(value, str):
            # Simple inversion: uppercase to lowercase, lowercase to uppercase
            return value.swapcase()
        return value
    
    def _increment_number(self, value: Any) -> Any:
        """
        Increment numeric values by 1.
        """
        if isinstance(value, (int, float)):
            return value + 1
        return value
    
    def _modify_policy_version(self, value: Any) -> Any:
        """
        Modify policy version strings.
        """
        if isinstance(value, str) and "v" in value.lower():
            # Increment version number
            parts = value.split("v")
            if len(parts) == 2:
                try:
                    version_num = int(parts[1])
                    return f"v{version_num + 1}"
                except ValueError:
                    pass
        return value
    
    def _alter_timestamp(self, value: Any) -> Any:
        """
        Alter timestamp strings (add 1 second).
        """
        if isinstance(value, str) and "T" in value:
            # Simple timestamp alteration: add 1 second
            # This is a simplified implementation
            return value.replace("Z", ".001Z")
        return value
    
    def _increment_version(self, version_str: str) -> str:
        """
        Increment version string.
        """
        if "v" in version_str.lower():
            parts = version_str.split("v")
            if len(parts) == 2:
                try:
                    version_num = int(parts[1])
                    return f"v{version_num + 1}"
                except ValueError:
                    pass
        return version_str + "-mutated"
    
    def _flip_hash_char(self, hash_str: str) -> str:
        """
        Flip one character in hash string.
        """
        if len(hash_str) > 0:
            # Flip first character
            first_char = hash_str[0]
            if first_char.isdigit():
                flipped = str((int(first_char) + 1) % 10)
            else:
                flipped = first_char.swapcase()
            return flipped + hash_str[1:]
        return hash_str
