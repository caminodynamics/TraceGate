"""
ProbeExecutionLoop - Orchestrates probe execution, drift detection, and probe generation

Deterministic fault-line testing harness execution loop:
- Run initial probe batch
- Detect drift
- Generate new probes
- Run new probes (one iteration only for now)
"""
import json
from typing import Dict, Any, List, Optional
from probe_runner import ProbeRunner, ProbeResult
from drift_detector import DriftDetector, DriftEvent, DriftType
from probe_generator import ProbeGenerator
from datetime import datetime


class ProbeExecutionLoop:
    """
    Orchestrates probe execution, drift detection, and probe generation.
    
    Execution loop:
    1. Run initial probe batch
    2. Detect drift
    3. Generate new probes from drift events
    4. Run new probes (one iteration only for now)
    """
    
    def __init__(self, traxes_adapter=None):
        """
        Initialize ProbeExecutionLoop.
        
        Args:
            traxes_adapter: TraxesAdapter instance. If None, creates default.
        """
        self.probe_runner = ProbeRunner(traxes_adapter)
        self.drift_detector = DriftDetector()
        self.probe_generator = ProbeGenerator()
        
        self.initial_probes: List[Dict[str, Any]] = []
        self.generated_probes: List[Dict[str, Any]] = []
        self.all_results: List[ProbeResult] = []
        self.drift_events: List[DriftEvent] = []
        self.iteration_count = 0
    
    def run(self, initial_probes: List[Dict[str, Any]], max_iterations: int = 1) -> Dict[str, Any]:
        """
        Run the probe execution loop.
        
        Args:
            initial_probes: List of initial probe dictionaries
            max_iterations: Maximum number of iterations (default: 1)
            
        Returns:
            Dictionary containing execution summary
        """
        self.initial_probes = initial_probes
        self.iteration_count = 0
        
        print(f"\n{'='*60}")
        print(f"PROBE EXECUTION LOOP STARTED")
        print(f"Initial probes: {len(initial_probes)}")
        print(f"Max iterations: {max_iterations}")
        print(f"{'='*60}")
        
        # Iteration 0: Run initial probes
        print(f"\n--- ITERATION {self.iteration_count}: Initial Probes ---")
        initial_results = self.probe_runner.run_probes(initial_probes)
        self.all_results.extend(initial_results)
        
        print(f"Executed {len(initial_results)} initial probes")
        
        # Detect drift from initial results
        drift_events = self._detect_drift(initial_results)
        self.drift_events.extend(drift_events)
        
        print(f"Detected {len(drift_events)} drift events")
        
        # Log drift events
        for event in drift_events:
            log = self.drift_detector.log_drift_event(event)
            print(f"\n{log}")
        
        # Generate new probes from drift events
        generated_probes = self._generate_probes(drift_events)
        self.generated_probes.extend(generated_probes)
        
        print(f"\nGenerated {len(generated_probes)} new probes from drift events")
        
        # Additional iterations
        for iteration in range(1, max_iterations):
            self.iteration_count = iteration
            print(f"\n--- ITERATION {iteration}: Generated Probes ---")
            
            if not generated_probes:
                print("No generated probes to execute")
                break
            
            # Run generated probes
            generated_results = self.probe_runner.run_probes(generated_probes)
            self.all_results.extend(generated_results)
            
            print(f"Executed {len(generated_results)} generated probes")
            
            # Detect drift from generated results
            new_drift_events = self._detect_drift(generated_results)
            self.drift_events.extend(new_drift_events)
            
            print(f"Detected {len(new_drift_events)} additional drift events")
            
            # Log new drift events
            for event in new_drift_events:
                log = self.drift_detector.log_drift_event(event)
                print(f"\n{log}")
            
            # Generate more probes (optional for future iterations)
            if iteration < max_iterations - 1:
                generated_probes = self._generate_probes(new_drift_events)
                self.generated_probes.extend(generated_probes)
                print(f"Generated {len(generated_probes)} additional probes")
        
        print(f"\n{'='*60}")
        print(f"PROBE EXECUTION LOOP COMPLETE")
        print(f"{'='*60}")
        
        # Return execution summary
        return self._get_summary()
    
    def _detect_drift(self, results: List[ProbeResult]) -> List[DriftEvent]:
        """
        Detect drift from probe results.
        
        Args:
            results: List of ProbeResults
            
        Returns:
            List of DriftEvents
        """
        drift_events = []
        
        for result in results:
            if result.error:
                # Skip results with errors
                continue
            
            if result.evaluate_artifact and result.replay_artifact:
                drift_event = self.drift_detector.compare(
                    result.evaluate_artifact,
                    result.replay_artifact
                )
                if drift_event:
                    drift_events.append(drift_event)
        
        return drift_events
    
    def _generate_probes(self, drift_events: List[DriftEvent]) -> List[Dict[str, Any]]:
        """
        Generate new probes from drift events.
        
        Args:
            drift_events: List of DriftEvents
            
        Returns:
            List of generated probe dictionaries
        """
        generated_probes = []
        
        for event in drift_events:
            # Generate 1-3 probes per drift event
            probes = self.probe_generator.generate_probes(event, count=3)
            generated_probes.extend(probes)
        
        return generated_probes
    
    def _get_summary(self) -> Dict[str, Any]:
        """
        Get execution summary.
        
        Returns:
            Dictionary containing execution summary
        """
        # Count drift events by type
        drift_counts = {}
        for event in self.drift_events:
            drift_type = event.drift_type.value
            drift_counts[drift_type] = drift_counts.get(drift_type, 0) + 1
        
        # Count successful vs failed probes
        successful_probes = sum(1 for r in self.all_results if r.error is None)
        failed_probes = sum(1 for r in self.all_results if r.error is not None)
        
        return {
            "initial_probes_count": len(self.initial_probes),
            "generated_probes_count": len(self.generated_probes),
            "total_probes_executed": len(self.all_results),
            "successful_probes": successful_probes,
            "failed_probes": failed_probes,
            "drift_events_count": len(self.drift_events),
            "drift_counts_by_type": drift_counts,
            "iterations_completed": self.iteration_count + 1,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_drift_events(self) -> List[DriftEvent]:
        """
        Get all detected drift events.
        """
        return self.drift_events
    
    def get_results(self) -> List[ProbeResult]:
        """
        Get all probe results.
        """
        return self.all_results
    
    def get_generated_probes(self) -> List[Dict[str, Any]]:
        """
        Get all generated probes.
        """
        return self.generated_probes
