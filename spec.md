Goal:
Test whether a decision system can be replayed after external state changes.

Core system:
- Inputs:
  - user_tier (string)
  - region (string)
  - feature_flag_safe_mode (boolean)

- Policy:
  IF user_tier == "premium"
  AND region == "EU"
  AND feature_flag_safe_mode == true
  THEN ALLOW
  ELSE DENY

Required outputs:
1. Decision result (ALLOW/DENY)
2. Decision artifact JSON containing:
   - inputs used
   - policy_version_hash
   - timestamp

Replay requirement:
Given only the artifact:
- system must be able to reproduce the same decision

Mutation rules (adversarial conditions):
- feature flag values may change after decision
- policy logic may change after decision
- external state may change after decision

Test cases:
1. No mutation → replay must match
2. Feature flag changes → must detect mismatch or explain failure
3. Policy changes → must detect mismatch or explain failure

Success criteria:
We are NOT testing correctness of business logic.
We are testing whether replay remains consistent under mutation.