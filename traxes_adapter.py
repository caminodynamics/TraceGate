"""
TraxesAdapter - Adapter for TRAXES integration

This adapter provides a clean interface to TRAXES functionality
via subprocess calls to the TRAXES Rust binary.

TRAXES is a Rust binary, not a Python library.
Integration is via CLI contract: traxes evaluate --input <json>
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
import sys


class TraxesAdapter:
    """
    Adapter for TRAXES integration via subprocess.
    
    TRAXES is a Rust binary located at /workspace/traxes.
    Integration is via CLI contract, not Python imports.
    """
    
    def __init__(self, traxes_binary_path: Optional[str] = None):
        """
        Initialize TraxesAdapter.
        
        Args:
            traxes_binary_path: Path to TRAXES binary. If None, uses default.
        """
        if traxes_binary_path:
            self.traxes_binary = Path(traxes_binary_path)
        else:
            # Default: look for traxes-demo binary in /workspace/traxes
            self.traxes_binary = Path("/workspace/traxes/target/release/traxes-demo")
        
        # Fallback to Windows executable
        if not self.traxes_binary.exists():
            self.traxes_binary = Path("/workspace/traxes/target/release/traxes-demo.exe")
        
        # Check if binary exists
        self.traxes_available = self.traxes_binary.exists()
        
        if not self.traxes_available:
            print(f"WARNING: TRAXES binary not found at {self.traxes_binary}")
            print("Build TRAXES with: cd /workspace/traxes && cargo build --release")
        else:
            print(f"TRAXES binary found: {self.traxes_binary}")
    
    def evaluate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an action using TRAXES binary.
        
        CLI Contract:
        traxes-demo eval --input <json>
        
        Args:
            input_data: Dictionary containing action/policy evaluation input
            
        Returns:
            Dictionary containing TRAXES decision artifact
            
        Raises:
            RuntimeError: If TRAXES binary not available or execution fails
        """
        if not self.traxes_available:
            raise RuntimeError(
                f"TRAXES binary not available at {self.traxes_binary}. "
                "Build with: cd /workspace/traxes && cargo build --release"
            )
        
        # Convert input to JSON
        input_json = json.dumps(input_data)
        
        # Build command
        command = [
            str(self.traxes_binary),
            "eval",
            "--input",
            input_json
        ]
        
        try:
            # Execute TRAXES binary
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check for errors
            if result.returncode != 0:
                raise RuntimeError(
                    f"TRAXES evaluation failed with exit code {result.returncode}\n"
                    f"stderr: {result.stderr}"
                )
            
            # Parse JSON output
            output_data = json.loads(result.stdout)
            
            return output_data
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("TRAXES evaluation timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse TRAXES output as JSON: {e}\n"
                f"stdout: {result.stdout}"
            )
        except Exception as e:
            raise RuntimeError(f"TRAXES evaluation failed: {e}")
    
    def replay(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replay a decision artifact using TRAXES binary.
        
        CLI Contract:
        traxes-demo replay --artifact <json>
        
        Args:
            artifact: Dictionary containing original decision artifact
            
        Returns:
            Dictionary containing replayed decision artifact
            
        Raises:
            RuntimeError: If TRAXES binary not available or execution fails
        """
        if not self.traxes_available:
            raise RuntimeError(
                f"TRAXES binary not available at {self.traxes_binary}. "
                "Build with: cd /workspace/traxes && cargo build --release"
            )
        
        # Convert artifact to JSON
        artifact_json = json.dumps(artifact)
        
        # Build command
        command = [
            str(self.traxes_binary),
            "replay",
            "--artifact",
            artifact_json
        ]
        
        try:
            # Execute TRAXES binary
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check for errors
            if result.returncode != 0:
                raise RuntimeError(
                    f"TRAXES replay failed with exit code {result.returncode}\n"
                    f"stderr: {result.stderr}"
                )
            
            # Parse JSON output
            output_data = json.loads(result.stdout)
            
            return output_data
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("TRAXES replay timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse TRAXES output as JSON: {e}\n"
                f"stdout: {result.stdout}"
            )
        except Exception as e:
            raise RuntimeError(f"TRAXES replay failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if TRAXES binary is available.
        """
        return self.traxes_available
    
    def get_traxes_path(self) -> Path:
        """
        Get the TRAXES binary path.
        """
        return self.traxes_binary


# Global adapter instance
_traxes_adapter = None


def get_traxes_adapter() -> TraxesAdapter:
    """
    Get the global TraxesAdapter instance.
    """
    global _traxes_adapter
    if _traxes_adapter is None:
        _traxes_adapter = TraxesAdapter()
    return _traxes_adapter
