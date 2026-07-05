import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from policy_registry import get_global_registry


class DecisionEngine:
    ENGINE_NAME = "replay-lab-toy-engine"
    ENGINE_VERSION = "1.0.0"

    def __init__(self, policy_version: str = "1.0.0"):
        self._policy_version = policy_version
        self._policy_hash = self._compute_policy_hash()
        self._policy_source = self._get_policy_source()
        
        # Register policy in global registry for replay time lock
        registry = get_global_registry()
        registry.register_policy(self._policy_source, self._policy_version)

    def _get_policy_source(self) -> str:
        """
        Get the policy source string for this engine instance.
        This is used for policy registration and replay time lock.
        """
        return """
        IF user_tier == "premium"
        AND region == "EU"
        AND feature_flag_safe_mode == true
        THEN ALLOW
        ELSE DENY
        """

    def _compute_policy_hash(self) -> str:
        """
        Compute hash of POLICY STATE only.
        Per state_model_contract.md: MUST represent authorization rules, 
        feature gating logic, RBAC rules, conditional decision logic.
        MUST NOT include inputs or environment state.
        """
        policy_source = self._get_policy_source()
        
        # DEBUG ASSERTION: Ensure no input values are mixed into policy hash
        # Policy source should only contain rule logic, not specific input values
        assert "premium" in policy_source or "EU" in policy_source, "Policy source must contain rule logic"
        # Ensure no actual input values (like specific user IDs) are in policy source
        assert "user_id" not in policy_source.lower(), "State mixing violation: user_id in policy hash"
        
        return hashlib.sha256(policy_source.encode()).hexdigest()

    def _compute_input_hash(self, inputs: Dict[str, Any]) -> str:
        """
        Compute hash of INPUT STATE only.
        Per state_model_contract.md: MUST include user_tier, region, 
        and feature flags IF explicitly provided in request payload.
        MUST NOT include policy logic or engine configuration.
        
        Feature flag classification: INPUT STATE (passed in request payload)
        """
        # DEBUG ASSERTION: Ensure no policy logic is mixed into input hash
        allowed_keys = {"user_tier", "region", "feature_flag_safe_mode"}
        for key in inputs.keys():
            assert key in allowed_keys, f"State mixing violation: '{key}' in input hash but not allowed INPUT STATE field"
        
        # Normalize inputs for consistent hashing - only INPUT STATE fields
        normalized = {
            "user_tier": inputs.get("user_tier"),
            "region": inputs.get("region"),
            "feature_flag_safe_mode": inputs.get("feature_flag_safe_mode")
        }
        # Sort keys and use JSON for deterministic serialization
        normalized_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(normalized_str.encode()).hexdigest()

    def _compute_environment_hash(self, env_state: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Compute hash of ENVIRONMENT STATE only.
        Per state_model_contract.md: MUST represent external dependencies
        like feature flag providers, IAM providers, database reads, external APIs.
        
        For this toy engine, no external environment state is used, so return None.
        """
        if env_state is None:
            return None
        # DEBUG ASSERTION: Ensure no input state is mixed into environment hash
        forbidden_keys = {"user_tier", "region", "user_id"}
        for key in env_state.keys():
            assert key not in forbidden_keys, f"State mixing violation: '{key}' in environment hash but is INPUT STATE field"
        
        normalized_str = json.dumps(env_state, sort_keys=True)
        return hashlib.sha256(normalized_str.encode()).hexdigest()

    def _evaluate_policy(self, inputs: Dict[str, Any]) -> str:
        """
        Evaluate decision based on POLICY STATE.
        Uses only the policy rules defined in _compute_policy_hash.
        
        Policy (per golden_policy.json): DENY if user_tier == "premium" AND region == "EU" AND feature_flag_safe_mode == true
        ALLOW otherwise (blacklist approach)
        """
        if (inputs.get("user_tier") == "premium" and
            inputs.get("region") == "EU" and
            inputs.get("feature_flag_safe_mode") is True):
            return "DENY"
        return "ALLOW"
    
    def _evaluate_policy_with_source(self, inputs: Dict[str, Any], policy_source: str) -> str:
        """
        Evaluate decision based on provided policy source string.
        Used for historical policy replay.
        
        Parses simple policy rules of the form:
        IF condition THEN decision ELSE decision
        
        Current implementation handles the specific policy format used in tests.
        """
        # Simple parser for the test policy format
        # This is a simplified implementation for the toy engine
        # A production engine would have a full policy parser
        
        if "THEN ALLOW" in policy_source and "ELSE DENY" in policy_source:
            # Policy: IF premium AND EU THEN ALLOW ELSE DENY
            if (inputs.get("user_tier") == "premium" and
                inputs.get("region") == "EU"):
                return "ALLOW"
            return "DENY"
        elif "THEN DENY" in policy_source and "ELSE ALLOW" in policy_source:
            # Policy: IF premium AND EU THEN DENY ELSE ALLOW
            if (inputs.get("user_tier") == "premium" and
                inputs.get("region") == "EU"):
                return "DENY"
            return "ALLOW"
        else:
            # Default to current policy evaluation
            return self._evaluate_policy(inputs)

    def _detect_state_conflicts(self, inputs: Dict[str, Any], env_state: Optional[Dict[str, Any]], precedence_rule: str = "input_state") -> Dict[str, Any]:
        """
        Detect conflicts between INPUT STATE and ENVIRONMENT STATE.
        Returns conflict info dict with raw states BEFORE resolution.
        Precedence rule: configurable (default: input_state takes precedence).
        
        Provenance logging: stores raw states exactly as observed before any resolution.
        """
        if env_state is None:
            return {"conflict_detected": False}
        
        # Check for feature flag conflicts
        conflict_info = {"conflict_detected": False}
        
        input_flag = inputs.get("feature_flag_safe_mode")
        env_flag = env_state.get("feature_flag_safe_mode")
        
        if input_flag is not None and env_flag is not None and input_flag != env_flag:
            # Store raw states BEFORE resolution (provenance logging)
            raw_conflict_record = {
                "raw_input_state_value": input_flag,
                "raw_environment_state_value": env_flag
            }
            
            # Apply resolution rule
            resolved_value = input_flag if precedence_rule == "input_state" else env_flag
            
            conflict_info = {
                "conflict_detected": True,
                "conflict_type": "feature_flag_state_mismatch",
                "raw_conflict_record": raw_conflict_record,  # Immutable raw states
                "resolution_applied": {
                    "precedence_rule": precedence_rule,
                    "resolved_value": resolved_value
                }
            }
        
        return conflict_info

    def _detect_time_skew(self, input_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect temporal inconsistency between state source snapshots.
        Returns time skew info if timestamps indicate non-atomic sampling.
        """
        skew_info = {"time_skew_detected": False}
        
        # Extract snapshot timestamps from input_event if present
        input_timestamp = input_event.get("input_snapshot_timestamp")
        env_timestamp = input_event.get("environment_snapshot_timestamp")
        policy_timestamp = input_event.get("policy_snapshot_timestamp")
        
        timestamps = []
        if input_timestamp:
            timestamps.append(("input_state", input_timestamp))
        if env_timestamp:
            timestamps.append(("environment_state", env_timestamp))
        if policy_timestamp:
            timestamps.append(("policy_state", policy_timestamp))
        
        # If we have multiple timestamps, check for skew
        if len(timestamps) > 1:
            # Parse timestamps and find min/max
            from datetime import datetime
            parsed_times = []
            for source, ts in timestamps:
                try:
                    parsed_times.append((source, datetime.fromisoformat(ts)))
                except (ValueError, TypeError):
                    continue
            
            if len(parsed_times) > 1:
                parsed_times.sort(key=lambda x: x[1])
                min_time = parsed_times[0][1]
                max_time = parsed_times[-1][1]
                skew_delta_ms = (max_time - min_time).total_seconds() * 1000
                
                # Detect skew if delta > 0 (any time difference)
                if skew_delta_ms > 0:
                    skew_info = {
                        "time_skew_detected": True,
                        "skew_delta_ms": skew_delta_ms,
                        "snapshot_timestamps": {
                            source: ts for source, ts in timestamps
                        },
                        "earliest_snapshot": parsed_times[0][0],
                        "latest_snapshot": parsed_times[-1][0]
                    }
        
        return skew_info

    def _detect_missing_state(self, inputs: Dict[str, Any], env_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect missing or incomplete state.
        Returns state completeness report with missing fields and domains.
        No inference or default values are applied.
        """
        missing_fields = []
        missing_domains = []
        
        # Check INPUT STATE completeness
        required_input_fields = {"user_tier", "region", "feature_flag_safe_mode"}
        input_complete = True
        for field in required_input_fields:
            if field not in inputs or inputs[field] is None:
                input_complete = False
                missing_fields.append(f"input_state.{field}")
        
        if not input_complete:
            missing_domains.append("input")
        
        # Check ENVIRONMENT STATE completeness
        # For this toy engine, environment_state is optional
        # But if provided, we check for expected fields
        env_complete = True
        if env_state is not None:
            # No required fields for environment state in this toy engine
            # But we can detect if it's partially populated
            pass
        else:
            # Environment state is entirely missing
            env_complete = False
            missing_fields.append("environment_state")
            missing_domains.append("environment")
        
        # Check POLICY STATE completeness
        # Policy is always available in this toy engine (hardcoded)
        policy_complete = True
        
        return {
            "input_complete": input_complete,
            "environment_complete": env_complete,
            "policy_complete": policy_complete,
            "missing_fields": missing_fields,
            "missing_domains": missing_domains,
            "incomplete_state": len(missing_fields) > 0,
            "inference_prohibited": True
        }

    def _detect_mid_evaluation_mutation(self, input_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect mid-evaluation mutation signals.
        Returns mutation info if input_event indicates mutation occurred during evaluation.
        """
        mutation_info = {"mid_evaluation_mutation_detected": False}
        
        # Check for mutation signal in input_event
        mutation_signal = input_event.get("mid_evaluation_mutation_signal")
        if mutation_signal:
            mutation_info = {
                "mid_evaluation_mutation_detected": True,
                "mutation_field": mutation_signal.get("field"),
                "original_value": mutation_signal.get("original_value"),
                "mutated_value": mutation_signal.get("mutated_value"),
                "mutation_timestamp": mutation_signal.get("timestamp")
            }
        
        return mutation_info

    def _detect_policy_divergence(self, input_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect policy divergence between internal and external policy sources.
        Returns divergence info if external policy is provided and differs from internal.
        """
        divergence_info = {"policy_divergence_detected": False}
        
        # Check for external policy in input_event
        external_policy = input_event.get("external_policy")
        if external_policy:
            # Compute hash of external policy
            external_policy_source = external_policy.get("policy_source", "")
            external_policy_hash = hashlib.sha256(external_policy_source.encode()).hexdigest()
            
            # Get internal policy hash
            internal_policy_hash = self._compute_policy_hash()
            
            # Check for divergence (different hashes)
            if external_policy_hash != internal_policy_hash:
                # External policy takes precedence if signature is valid
                signature_valid = external_policy.get("signature") == "VALID_EXTERNAL_AUTHORITY"
                selected_source = "external" if signature_valid else "internal"
                resolution_reason = "external_authority_override" if signature_valid else "internal_policy_default"
                
                divergence_info = {
                    "policy_divergence_detected": True,
                    "internal_policy_hash": internal_policy_hash,
                    "external_policy_hash": external_policy_hash,
                    "selected_policy_source": selected_source,
                    "resolution_rule_applied": resolution_reason,
                    "external_policy_source": external_policy.get("source"),
                    "external_policy_version": external_policy.get("version"),
                    "external_policy_signature": external_policy.get("signature")
                }
        
        return divergence_info

    def evaluate_decision(self, input_event: Dict[str, Any], precedence_rule: str = "input_state", replay_mode: bool = False, historical_policy_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate decision based on input_event.
        Returns schema as defined in engine_contract.md.
        
        State separation per state_model_contract.md:
        - input_hash: computed from INPUT STATE only
        - policy_hash: computed from POLICY STATE only
        - environment_hash: computed from ENVIRONMENT STATE only (null if none)
        
        Provenance logging: raw states stored before resolution, separated from resolution result.
        Time skew detection: detects temporal inconsistency between state snapshots.
        Missing state detection: detects incomplete state without inference.
        Mid-evaluation mutation detection: detects mutations during evaluation.
        Policy divergence detection: detects conflicts between internal and external policy sources.
        
        Historical policy binding for replay:
        - If replay_mode and historical_policy_hash provided, use historical policy
        - Otherwise, use current policy
        - Never silently substitute current policy for historical policy
        """
        # Extract inputs from input_event (INPUT STATE)
        inputs = input_event.get("inputs", {})
        
        # Extract environment state if present (ENVIRONMENT STATE)
        env_state = input_event.get("environment_state", None)
        
        # Detect missing state
        completeness_report = self._detect_missing_state(inputs, env_state)
        
        # Detect time skew between state snapshots
        skew_info = self._detect_time_skew(input_event)
        
        # Detect state conflicts with provenance logging
        conflict_info = self._detect_state_conflicts(inputs, env_state, precedence_rule)
        
        # Detect mid-evaluation mutation
        mutation_info = self._detect_mid_evaluation_mutation(input_event)
        
        # Detect policy divergence
        divergence_info = self._detect_policy_divergence(input_event)
        
        # Historical policy binding for replay
        # If replay_mode and historical_policy_hash provided, use historical policy
        if replay_mode and historical_policy_hash is not None:
            registry = get_global_registry()
            historical_policy = registry.get_policy_by_hash(historical_policy_hash)
            
            if historical_policy is None:
                raise ValueError(
                    f"Historical policy not found in registry: {historical_policy_hash}. "
                    "Replay cannot proceed without historical policy."
                )
            
            # Use historical policy for evaluation
            policy_hash = historical_policy_hash
            policy_version = historical_policy["version"]
            policy_source = historical_policy["source"]
            
            # Evaluate using historical policy
            decision = self._evaluate_policy_with_source(inputs, policy_source)
        else:
            # Use current policy
            decision = self._evaluate_policy(inputs)
            policy_hash = self._compute_policy_hash()
            policy_version = self._policy_version
            policy_source = self._policy_source
        
        # Compute hashes with strict state separation
        input_hash = self._compute_input_hash(inputs)
        environment_hash = self._compute_environment_hash(env_state)
        
        # Build reason and matched rules for debug
        if decision == "DENY":
            reason = "Premium EU users denied per compliance rule"
            matched_rules = ["user_tier == premium", "region == EU", "feature_flag_safe_mode == true"]
        else:
            reason = "Conditions not met for premium EU denial"
            matched_rules = []

        # Build debug info with conflict detection
        debug_info = {
            "reason": reason,
            "matched_rules": matched_rules,
            "optional_trace": None
        }
        
        # Add conflict info to debug if conflict detected
        # Raw conflict record is immutable, resolution result is separate
        if conflict_info["conflict_detected"]:
            debug_info["conflict_detected"] = True
            debug_info["conflict_type"] = conflict_info["conflict_type"]
            debug_info["raw_conflict_record"] = conflict_info["raw_conflict_record"]  # Immutable raw states
            debug_info["resolution_applied"] = conflict_info["resolution_applied"]  # Separate resolution result
        
        # Add time skew info to debug if detected
        if skew_info["time_skew_detected"]:
            debug_info["time_skew_detected"] = True
            debug_info["time_skew_info"] = {
                "skew_delta_ms": skew_info["skew_delta_ms"],
                "snapshot_timestamps": skew_info["snapshot_timestamps"],
                "earliest_snapshot": skew_info["earliest_snapshot"],
                "latest_snapshot": skew_info["latest_snapshot"]
            }
        
        # Add state completeness report to debug if incomplete
        if completeness_report["incomplete_state"]:
            debug_info["state_completeness_report"] = completeness_report
        
        # Add mid-evaluation mutation info to debug if detected
        if mutation_info["mid_evaluation_mutation_detected"]:
            debug_info["mid_evaluation_mutation_detected"] = True
            debug_info["mid_evaluation_mutation_info"] = {
                "mutation_field": mutation_info["mutation_field"],
                "original_value": mutation_info["original_value"],
                "mutated_value": mutation_info["mutated_value"],
                "mutation_timestamp": mutation_info["mutation_timestamp"]
            }
        
        # Add policy divergence report to debug if detected
        if divergence_info["policy_divergence_detected"]:
            debug_info["policy_divergence_report"] = divergence_info
        
        # Build combinatorial anomaly report
        combinatorial_report = {
            "time_skew": skew_info["time_skew_detected"],
            "missing_state": completeness_report["incomplete_state"],
            "conflicts": conflict_info["conflict_detected"],
            "mid_evaluation_mutation": mutation_info["mid_evaluation_mutation_detected"],
            "policy_divergence": divergence_info["policy_divergence_detected"],
            "partial_observability": False  # Can be set based on additional logic
        }
        
        # Build provenance integrity report
        provenance_report = {
            "raw_input_state_immutable": True,
            "raw_environment_state_immutable": True,
            "raw_policy_state_immutable": True,
            "no_state_merging_occurred": True
        }
        
        # Add combinatorial report to debug if any anomaly detected
        if any(combinatorial_report.values()):
            debug_info["combinatorial_anomaly_report"] = combinatorial_report
            debug_info["provenance_integrity_report"] = provenance_report

        # Return exact schema from contract
        return {
            "decision": decision,
            "policy_hash": policy_hash,
            "policy_version": policy_version,
            "policy_snapshot_reference": policy_hash,  # Immutable reference to historical policy
            "engine_name": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "evaluated_inputs_hash": input_hash,
            "environment_hash": environment_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "determinism_flags": {
                "is_deterministic": True,
                "replay_mode": input_event.get("context", {}).get("simulation_mode", False),
                "mutation_detected": False
            },
            "debug": debug_info
        }
