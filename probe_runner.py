"""
ProbeRunner - Executes probes against TRAXES binary

Deterministic fault-line testing harness for TRAXES.
"""
import json
from typing import Dict, Any, List, Optional
from traxes_adapter import TraxesAdapter
from datetime import datetime


class ProbeResult:
    """
    Result of a probe execution.
    """
    def __init__(self, probe: Dict[str, Any], evaluate_artifact: Optional[Dict[str, Any]], 
                 replay_artifact: Optional[Dict[str, Any]], error: Optional[str] = None):
        self.probe = probe
        self.evaluate_artifact = evaluate_artifact
        self.replay_artifact = replay_artifact
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        """
        return {
            "probe": self.probe,
            "evaluate_artifact": self.evaluate_artifact,
            "replay_artifact": self.replay_artifact,
            "error": self.error,
            "timestamp": self.timestamp
        }


class ProbeRunner:
    """
    Executes probes against TRAXES binary via subprocess.
    
    Each probe:
    - Sends JSON input to TRAXES
    - Receives JSON output
    - Stores full artifact
    """
    
    def __init__(self, traxes_adapter: Optional[TraxesAdapter] = None):
        """
        Initialize ProbeRunner.
        
        Args:
            traxes_adapter: TraxesAdapter instance. If None, creates default.
        """
        self.adapter = traxes_adapter or TraxesAdapter()
        self.results: List[ProbeResult] = []
    
    def run_probe(self, probe: Dict[str, Any]) -> ProbeResult:
        """
        Run a single probe against TRAXES.
        
        Args:
            probe: Dictionary containing probe input data
            
        Returns:
            ProbeResult containing evaluate and replay artifacts
        """
        if not self.adapter.is_available():
            return ProbeResult(
                probe=probe,
                evaluate_artifact=None,
                replay_artifact=None,
                error=f"TRAXES binary not available at {self.adapter.get_traxes_path()}"
            )
        
        # Step 1: Evaluate
        try:
            evaluate_artifact = self.adapter.evaluate(probe)
        except Exception as e:
            return ProbeResult(
                probe=probe,
                evaluate_artifact=None,
                replay_artifact=None,
                error=f"Evaluate failed: {str(e)}"
            )
        
        # Step 2: Replay
        try:
            replay_artifact = self.adapter.replay(evaluate_artifact)
        except Exception as e:
            # Replay failure is not a probe failure - still return evaluate artifact
            return ProbeResult(
                probe=probe,
                evaluate_artifact=evaluate_artifact,
                replay_artifact=None,
                error=f"Replay failed: {str(e)}"
            )
        
        # Success
        result = ProbeResult(
            probe=probe,
            evaluate_artifact=evaluate_artifact,
            replay_artifact=replay_artifact,
            error=None
        )
        
        self.results.append(result)
        return result
    
    def run_probes(self, probes: List[Dict[str, Any]]) -> List[ProbeResult]:
        """
        Run multiple probes against TRAXES.
        
        Args:
            probes: List of probe dictionaries
            
        Returns:
            List of ProbeResults
        """
        results = []
        for probe in probes:
            result = self.run_probe(probe)
            results.append(result)
        return results
    
    def get_results(self) -> List[ProbeResult]:
        """
        Get all probe results.
        """
        return self.results
    
    def clear_results(self):
        """
        Clear all stored results.
        """
        self.results = []
