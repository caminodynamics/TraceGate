# Replay Lab State Model Contract

This document defines how all engine implementations MUST classify state for deterministic replay.

It resolves ambiguity between inputs, policy, and environment.

---

## 1. STATE CLASSIFICATION MODEL

Every engine MUST classify all evaluation data into exactly 3 buckets:

---

### A. INPUT STATE (Immutable Facts)

Definition:
Data that represents the event being evaluated.

Must include:

- user_id (or equivalent)
- user_tier
- region
- request parameters
- feature flags ONLY if explicitly provided as part of request payload

Rules:
- MUST be included in evaluated_inputs_hash
- MUST NOT include policy logic
- MUST NOT include engine configuration

---

### B. POLICY STATE (Evaluation Logic)

Definition:
Rules used to evaluate inputs.

Must include:

- authorization rules
- feature gating logic (if defined server-side)
- RBAC rules
- conditional decision logic

Rules:
- MUST be represented by policy_hash
- MUST NOT be included in input hash
- MUST be versioned independently of inputs

---

### C. ENVIRONMENT STATE (External / System Context)

Definition:
All external or mutable runtime dependencies.

Includes:

- feature flag provider state (if external)
- IAM provider state
- database reads
- external API responses
- system time (unless injected)

Rules:
- MUST be explicitly snapshot OR pinned
- MUST NOT be mixed into input_hash
- MUST be referenced via environment_hash if used

---

## 2. REQUIRED HASH FUNCTIONS

Every engine MUST implement:

### 2.1 Input Hash
```python
def compute_input_hash(input_state: dict) -> str:
```

Must ONLY include INPUT STATE.

### 2.2 Policy Hash
```python
def get_policy_hash() -> str:
```

Must ONLY represent POLICY STATE.

### 2.3 Environment Hash (optional but recommended)
```python
def compute_environment_hash(env_state: dict) -> str:
```

Must represent all ENVIRONMENT STATE used in evaluation.

---

## 3. CRITICAL RULE (NO MIXING)

Under no circumstances may an engine:

- mix policy state into input hash
- mix environment state into input hash
- mix inputs into policy hash

Violation of this rule = NON-DETERMINISTIC ENGINE.

---

## 4. REPLAY VALIDATION RULE

Replay Lab will validate:

| Component | Must Match for Replay Success |
|-----------|-------------------------------|
| decision | required |
| input_hash | required |
| policy_hash | required |
| environment_hash | required if present |

---

## 5. FEATURE FLAG RULE (IMPORTANT)

Feature flags MUST be classified as ONE of:

- Input State (if passed in request)
- Policy State (if defined in engine)
- Environment State (if fetched externally)

They cannot be unclassified.

---

## 6. FAILURE MODES THIS MODEL EXPOSES

This model explicitly detects:

- hidden coupling between flags and inputs
- policy drift across versions
- environment-induced nondeterminism

---

## 7. ENGINE COMPLIANCE RULE

If an engine cannot cleanly separate these three states:

→ it is considered NOT REPLAYABLE under Replay Lab
