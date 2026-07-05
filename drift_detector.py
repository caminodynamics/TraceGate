"""
DriftDetector - Compares evaluate output vs replay output

Detects differences in:
- decision
- artifact hash
- policy version
- temporal metadata
"""
import json
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime


class DriftType(Enum):
    """
    Types of drift that can be detected.
    """
    STATE = "state"  # State drift: input state differences
    TEMPORAL = "temporal"  # Temporal drift: timestamp/version differences
    SEMANTIC = "semantic"  # Semantic drift: decision differences
    ARTIFACT = "artifact"  # Artifact drift: hash/structure differences


class DriftEvent:
    """
    A detected drift event with full context.
    """
    def __init__(self, drift_type: DriftType, evaluate_artifact: Dict[str, Any],
                 replay_artifact: Dict[str, Any], differences: Dict[str, Any]):
        self.drift_type = drift_type
        self.evaluate_artifact = evaluate_artifact
        self.replay_artifact = replay_artifact
        self.differences = differences
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        """
        return {
            "drift_type": self.drift_type.value,
            "evaluate_artifact": self.evaluate_artifact,
            "replay_artifact": self.replay_artifact,
            "differences": self.differences,
            "timestamp": self.timestamp
        }


class DriftDetector:
    """
    Compares evaluate output vs replay output to detect drift.
    
    Detects differences in:
    - decision
    - artifact hash
    - policy version
    - temporal metadata
    """
    
    def __init__(self):
        self.drift_events: List[DriftEvent] = []
    
    def compare(self, evaluate_artifact: Dict[str, Any], 
                replay_artifact: Dict[str, Any]) -> Optional[DriftEvent]:
        """
        Compare evaluate and replay artifacts to detect drift.
        
        Args:
            evaluate_artifact: Original evaluation artifact
            replay_artifact: Replay evaluation artifact
            
        Returns:
            DriftEvent if drift detected, None otherwise
        """
        differences = {}
        
        # Check decision drift
        if evaluate_artifact.get("decision") != replay_artifact.get("decision"):
            differences["decision"] = {
                "evaluate": evaluate_artifact.get("decision"),
                "replay": replay_artifact.get("decision")
            }
        
        # Check policy hash drift
        if evaluate_artifact.get("policy_hash") != replay_artifact.get("policy_hash"):
            differences["policy_hash"] = {
                "evaluate": evaluate_artifact.get("policy_hash"),
                "replay": replay_artifact.get("policy_hash")
            }
        
        # Check policy version drift
        if evaluate_artifact.get("policy_version") != replay_artifact.get("policy_version"):
            differences["policy_version"] = {
                "evaluate": evaluate_artifact.get("policy_version"),
                "replay": replay_artifact.get("policy_version")
            }
        
        # Check temporal metadata drift
        if evaluate_artifact.get("timestamp") != replay_artifact.get("timestamp"):
            differences["timestamp"] = {
                "evaluate": evaluate_artifact.get("timestamp"),
                "replay": replay_artifact.get("timestamp")
            }
        
        # Check artifact hash drift (if present)
        if evaluate_artifact.get("sha256_hash") != replay_artifact.get("sha256_hash"):
            differences["sha256_hash"] = {
                "evaluate": evaluate_artifact.get("sha256_hash"),
                "replay": replay_artifact.get("sha256_hash")
            }
        
        # Check decision_id drift
        if evaluate_artifact.get("decision_id") != replay_artifact.get("decision_id"):
            differences["decision_id"] = {
                "evaluate": evaluate_artifact.get("decision_id"),
                "replay": replay_artifact.get("decision_id")
            }
        
        # Classify drift type
        drift_type = self._classify_drift(differences)
        
        if drift_type:
            event = DriftEvent(
                drift_type=drift_type,
                evaluate_artifact=evaluate_artifact,
                replay_artifact=replay_artifact,
                differences=differences
            )
            self.drift_events.append(event)
            return event
        
        return None
    
    def _classify_drift(self, differences: Dict[str, Any]) -> Optional[DriftType]:
        """
        Classify drift type based on differences.
        
        Args:
            differences: Dictionary of detected differences
            
        Returns:
            DriftType if drift detected, None otherwise
        """
        if not differences:
            return None
        
        # Semantic drift: decision changed
        if "decision" in differences:
            return DriftType.SEMANTIC
        
        # Temporal drift: timestamp or policy version changed
        if "timestamp" in differences or "policy_version" in differences:
            return DriftType.TEMPORAL
        
        # Artifact drift: hash or structure changed
        if "policy_hash" in differences or "sha256_hash" in differences or "decision_id" in differences:
            return DriftType.ARTIFACT
        
        # State drift: other state differences
        return DriftType.STATE
    
    def get_drift_events(self) -> List[DriftEvent]:
        """
        Get all detected drift events.
        """
        return self.drift_events
    
    def clear_drift_events(self):
        """
        Clear all stored drift events.
        """
        self.drift_events = []
    
    def log_drift_event(self, event: DriftEvent) -> str:
        """
        Log drift event with full context.
        
        Args:
            event: DriftEvent to log
            
        Returns:
            Formatted log string
        """
        log_lines = [
            f"[{event.timestamp}] DRIFT DETECTED",
            f"Type: {event.drift_type.value}",
            f"Differences: {json.dumps(event.differences, indent=2)}",
            f"Evaluate Artifact: {json.dumps(event.evaluate_artifact, indent=2)}",
            f"Replay Artifact: {json.dumps(event.replay_artifact, indent=2)}"
        ]
        return "\n".join(log_lines)
