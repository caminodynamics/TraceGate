# TraceGate

Deterministic execution trace validation and drift detection system for the TRAXES execution engine

## Overview

TraceGate is an execution integrity layer designed to validate deterministic decision systems under adversarial conditions, temporal mutation, and policy evolution.

It provides a strict boundary between:

- **Execution** (TRAXES)
- **Verification** (TraceGate)

TraceGate operates as an external validation system that enforces correctness across evaluation, replay, and historical reconstruction of execution decisions.

## Design Goals

TraceGate is built around four core invariants:

### 1. Deterministic Isolation

Execution results must be reproducible under identical input, policy state, and temporal context.

### 2. Temporal Integrity

Replay operations must strictly bind to the historical policy and environment snapshot at time of evaluation.

### 3. Artifact Immutability

Execution artifacts are immutable and must not be modified, reconstructed, or normalized during replay.

### 4. Drift Detectability

Any divergence between evaluate-time and replay-time execution must be explicitly classified and surfaced.

## System Architecture

TraceGate operates as a subprocess-based validation layer over the TRAXES binary.

```
┌────────────────────┐
│   TraceGate        │
│  (Python Layer)    │
└─────────┬──────────┘
          │ subprocess JSON
          ▼
┌────────────────────┐
│     TRAXES         │
│ (Rust Execution    │
│     Engine)        │
└────────────────────┘
```

### Key Properties

- No shared memory with TRAXES
- No direct language bindings (no FFI, no PyO3)
- Strict CLI contract enforcement
- JSON-only communication boundary

## Core Components

### 1. Probe Runner

Responsible for executing structured test probes against TRAXES.

- Executes CLI calls via `subprocess.run`
- Sends serialized JSON input
- Captures structured output artifacts
- Enforces timeout and exit code policy

### 2. Drift Detector

Compares execution states across evaluation and replay cycles.

Detects:

- Decision drift (allow → deny)
- Temporal drift (policy version mismatch)
- Artifact drift (hash divergence)
- State drift (input/environment inconsistency)

Each drift is emitted as a structured event with classification metadata.

### 3. Probe Generator

Generates mutation probes from observed drift signatures.

Mutation strategies include:

- Boolean state inversion
- Structural input perturbation
- Policy condition rewriting
- Temporal version shifts

Probe generation is deterministic and rule-based. No probabilistic or learned components are used.

### 4. Execution Loop Engine

Orchestrates the full fault-line testing cycle:

1. Execute probe batch
2. Collect TRAXES outputs
3. Detect drift events
4. Generate derived probes
5. Repeat for configured iteration depth

## CLI Contract (TRAXES Integration)

TraceGate interacts with TRAXES exclusively via the following interface:

### Evaluate

```bash
traxes_demo eval --input '<JSON>'
```

### Replay

```bash
traxes_demo replay --artifact '<JSON>'
```

## Exit Code Semantics

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | Evaluation or replay failure |
| 2    | Invalid input or artifact |
| 3    | Policy evaluation error |
| 4    | Temporal drift detected |

TraceGate treats exit codes as semantic signals, not generic errors.

## Drift Classification Model

TraceGate classifies system divergence into four categories:

- **Temporal Drift**: replay does not use historical policy snapshot
- **Semantic Drift**: identical policy structure yields different decisions
- **State Drift**: input/environment inconsistency across evaluation boundaries
- **Artifact Drift**: mutation of immutable execution artifacts

Each drift event is assigned:

- drift type
- severity level
- context hash
- execution trace reference

## Determinism Guarantees

TraceGate enforces the following system-level guarantees:

- Replay must be identical under identical historical context
- Policy versioning is strictly immutable once referenced in artifacts
- No fallback to current policy is permitted during replay
- No silent normalization of input or output structures
- All drift must be explicitly observable

## Failure Model

TraceGate treats the following as hard failures:

- Replay using non-historical policy state
- Artifact mutation during replay
- Silent substitution of policy versions
- Undetected semantic divergence between evaluate/replay cycles

## Non-Goals

TraceGate explicitly does not:

- Execute policies itself
- Replace the TRAXES decision engine
- Perform probabilistic inference
- Provide LLM-based evaluation or scoring
- Modify execution behavior inside TRAXES

TraceGate is strictly a verification and validation boundary system.

## Intended Use Cases

- Deterministic policy engine validation
- Execution replay verification
- Temporal consistency testing
- Adversarial input mutation testing
- Audit-grade decision trace validation

## System Status

TraceGate is currently in active validation against the TRAXES execution engine interface.

The system is designed to evolve through observed drift patterns, not manual test expansion.

## License / Deployment Model

TraceGate is intended for:

- local execution environments
- CI-integrated deterministic validation pipelines
- offline or air-gapped verification systems
