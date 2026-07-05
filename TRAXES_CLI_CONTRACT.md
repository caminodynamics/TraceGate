# TRAXES CLI Contract

## Overview

TRAXES is a Rust binary that integrates with ReplayLab via subprocess execution. This document defines the strict CLI contract between ReplayLab and the TRAXES binary.

## Binary Location

- **Default path**: `/workspace/traxes/target/release/traxes-demo`
- **Windows fallback**: `/workspace/traxes/target/release/traxes-demo.exe`
- **Build command**: `cd /workspace/traxes && cargo build --release`

## CLI Commands

### 1. Evaluate Command

Evaluates an action against a policy and produces a decision artifact.

**Command:**
```bash
traxes-demo eval --input <json>
```

**Input Format (JSON via stdin or --input):**
```json
{
  "tool": "AWS_RDS_PROVISION",
  "environment": "staging",
  "parameters": {
    "instance_type": "t3.micro",
    "instance_cost_per_hour": 0.015
  },
  "policy_bundle": "infra-cost-limit-v1"
}
```

**Output Format (JSON via stdout):**
```json
{
  "artifact_version": "1.0.0",
  "artifact_type": "pre_execution_decision",
  "decision_id": "dec_84b52d8256e3414f914f3047f2dd2cd0",
  "timestamp": "2026-06-29T18:04:51.924457800+00:00",
  "decision": "ALLOW",
  "tool": "AWS_RDS_PROVISION",
  "environment": "staging",
  "policy_bundle": "infra-cost-limit-v1",
  "policy_hash": "785e022b9921ee6a43ab5044cc8e4a67930c936a1a521f4479269e47eacc52e8",
  "sha256_hash": "e3665d8564c753be7334b9e77c6585d2d4bbd5d74255619111d385b880bd62f0",
  "engine": {
    "name": "Traxes",
    "engine_version": "0.3.2",
    "policy_bundle_id": "infra-cost-limit-v1"
  },
  "proposed_action": {
    "tool": "AWS_RDS_PROVISION",
    "environment": "staging",
    "parameters": {
      "instance_type": "t3.micro",
      "instance_cost_per_hour": 0.015
    }
  },
  "rule_evaluation": {
    "rule_id": "infra-cost-limit",
    "field": "proposed_action.parameters.instance_type",
    "observed_value": "t3.micro",
    "operator": "infra-cost-limit",
    "evaluation_expression": "proposed_action.parameters.instance_type not_in policy",
    "evaluation_result": false
  },
  "performance": {
    "evaluation_latency_us": 230.0,
    "decision_latency_us": 4.8,
    "artifact_write_latency_us": 41.7
  },
  "side_effect_prevention": {
    "decision_effect": "ALLOW"
  },
  "execution_status": "executed"
}
```

**Exit Codes:**
- `0`: Success
- `1`: Evaluation error
- `2`: Invalid input
- `3`: Policy error

### 2. Replay Command

Replays a decision artifact using the original policy version.

**Command:**
```bash
traxes-demo replay --artifact <json>
```

**Input Format (JSON via stdin or --artifact):**
```json
{
  "artifact_version": "1.0.0",
  "artifact_type": "pre_execution_decision",
  "decision_id": "dec_84b52d8256e3414f914f3047f2dd2cd0",
  "timestamp": "2026-06-29T18:04:51.924457800+00:00",
  "decision": "ALLOW",
  "policy_bundle": "infra-cost-limit-v1",
  "policy_hash": "785e022b9921ee6a43ab5044cc8e4a67930c936a1a521f4479269e47eacc52e8",
  "proposed_action": {
    "tool": "AWS_RDS_PROVISION",
    "environment": "staging",
    "parameters": {
      "instance_type": "t3.micro",
      "instance_cost_per_hour": 0.015
    }
  }
}
```

**Output Format (JSON via stdout):**
```json
{
  "artifact_version": "1.0.0",
  "artifact_type": "replay_decision",
  "decision_id": "dec_84b52d8256e3414f914f3047f2dd2cd0",
  "timestamp": "2026-06-29T18:04:51.924457800+00:00",
  "replay_timestamp": "2026-06-29T18:05:00.000000000+00:00",
  "decision": "ALLOW",
  "replay_decision": "ALLOW",
  "decision_match": true,
  "policy_bundle": "infra-cost-limit-v1",
  "policy_hash": "785e022b9921ee6a43ab5044cc8e4a67930c936a1a521f4479269e47eacc52e8",
  "engine": {
    "name": "Traxes",
    "engine_version": "0.3.2"
  },
  "replay_performance": {
    "evaluation_latency_us": 230.0,
    "decision_latency_us": 4.8
  }
}
```

**Exit Codes:**
- `0`: Success
- `1`: Replay error
- `2`: Invalid artifact
- `3`: Historical policy not found
- `4`: Temporal drift detected

## Integration Requirements

### ReplayLab Integration

ReplayLab must:
1. Call TRAXES binary via subprocess
2. Pass JSON input via `--input` flag
3. Receive JSON output via stdout
4. Parse JSON response
5. Handle exit codes appropriately
6. NOT use Python imports of TRAXES
7. NOT use pip install for TRAXES

### Error Handling

ReplayLab must handle:
- Binary not found (build instruction)
- Timeout (30 second default)
- Invalid JSON output
- Non-zero exit codes
- Temporal drift errors (exit code 4)

## Contract Invariants

1. **Deterministic Output**: Same input always produces same output
2. **JSON Format**: All I/O is valid JSON
3. **Exit Codes**: Non-zero exit codes indicate errors
4. **No Side Effects**: Evaluation has no external side effects
5. **Policy Binding**: Replay uses historical policy from artifact
6. **Temporal Integrity**: Replay fails if historical policy unavailable
