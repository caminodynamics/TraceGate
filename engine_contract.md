# Replay Lab Engine Interface Contract

This document defines the ONLY valid interface between Replay Lab and any external decision engine (including Traxes).

The goal is strict reproducibility, deterministic replay, and plug-compatible engine swapping.

---

## 1. Core Function

Every engine MUST implement:

```python
def evaluate_decision(input_event: dict) -> dict:
```

## 2. Input Schema

```json
{
  "event_id": "string",
  "timestamp": "ISO-8601 string",
  "inputs": {
    "user_tier": "string",
    "region": "string",
    "feature_flag_safe_mode": "boolean"
  },
  "context": {
    "source": "replay-lab | traxes | external",
    "simulation_mode": "boolean"
  }
}
```

Rules:
- input_event MUST be treated as immutable
- engines MUST NOT modify input_event
- all required decision logic MUST derive from this object or pinned policy state

## 3. REQUIRED RETURN SCHEMA (CRITICAL)

Every engine MUST return EXACTLY this structure:

```json
{
  "decision": "ALLOW | DENY",
  "policy_hash": "string",
  "engine_name": "string",
  "engine_version": "string",
  "evaluated_inputs_hash": "string",
  "environment_hash": "string | null",
  "timestamp": "ISO-8601 string",
  "determinism_flags": {
    "is_deterministic": "boolean",
    "replay_mode": "boolean",
    "mutation_detected": "boolean"
  },
  "debug": {
    "reason": "string",
    "matched_rules": ["string"],
    "optional_trace": "string | null"
  }
}
```

## 4. Determinism Rules

A run is considered deterministic if:
- same input_event
- same policy_hash
- same engine_version

→ MUST produce identical return payload (byte-equivalent for all fields except timestamp if explicitly configured otherwise)

## 5. Policy Hash Requirements

policy_hash MUST:
- represent EXACT rule set used in evaluation
- change whenever ANY rule logic changes
- be stable across identical builds
- be included in every artifact

## 6. Evaluated Inputs Hash

evaluated_inputs_hash MUST:
- be a deterministic hash of normalized input_event.inputs only
- exclude timestamps and context metadata
- be consistent across replays

## 7. Replay Contract

Replay Lab will:
- Call evaluate_decision(input_event)
- Store full return artifact
- Mutate external state
- Re-run evaluation using same input_event
- Compare:
  - decision
  - policy_hash
  - evaluated_inputs_hash

## 8. Mutation Semantics

Engines MUST tolerate:
- feature flag changes
- policy changes
- external state changes

BUT:
- They MUST reflect those changes via:
  - policy_hash change OR
  - deterministic mismatch signaling in determinism_flags

## 9. Engine Identity

ENGINE_NAME = "string"
ENGINE_VERSION = "string"

## 10. Non-Goals

This contract does NOT require:
- distributed systems
- production infrastructure
- databases
- external APIs
- performance optimization