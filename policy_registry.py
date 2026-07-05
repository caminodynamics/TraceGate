"""
Policy Registry for Historical Policy Binding

Stores immutable policy snapshots by version/hash to enable replay time lock.
Replay must use historical policy from artifact, never current policy.
"""
import hashlib
from typing import Dict, Optional


class PolicyRegistry:
    """
    Registry for storing and retrieving historical policy snapshots.
    Policies are indexed by hash and version for replay time lock.
    """
    
    def __init__(self):
        self._policies: Dict[str, Dict[str, str]] = {}  # policy_hash -> {version, source}
        self._version_to_hash: Dict[str, str] = {}  # version -> policy_hash
    
    def register_policy(self, policy_source: str, version: str) -> str:
        """
        Register a policy snapshot with its version.
        Returns the policy hash.
        """
        policy_hash = hashlib.sha256(policy_source.encode()).hexdigest()
        
        self._policies[policy_hash] = {
            "version": version,
            "source": policy_source
        }
        
        self._version_to_hash[version] = policy_hash
        
        return policy_hash
    
    def get_policy_by_hash(self, policy_hash: str) -> Optional[Dict[str, str]]:
        """
        Retrieve policy snapshot by hash.
        Returns None if policy not found.
        """
        return self._policies.get(policy_hash)
    
    def get_policy_by_version(self, version: str) -> Optional[Dict[str, str]]:
        """
        Retrieve policy snapshot by version.
        Returns None if policy not found.
        """
        policy_hash = self._version_to_hash.get(version)
        if policy_hash:
            return self._policies.get(policy_hash)
        return None
    
    def policy_exists(self, policy_hash: str) -> bool:
        """
        Check if policy exists in registry.
        """
        return policy_hash in self._policies
    
    def remove_policy(self, policy_hash: str) -> bool:
        """
        Remove policy from registry by hash.
        Returns True if policy was removed, False if not found.
        """
        if policy_hash in self._policies:
            policy_version = self._policies[policy_hash]["version"]
            del self._policies[policy_hash]
            if policy_version in self._version_to_hash:
                del self._version_to_hash[policy_version]
            return True
        return False


# Global policy registry instance
_global_registry = PolicyRegistry()


def get_global_registry() -> PolicyRegistry:
    """Get the global policy registry instance."""
    return _global_registry
