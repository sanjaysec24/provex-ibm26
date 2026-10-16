from typing import Any, Dict, List, Optional
from app.policy.engine import PolicyDecisionResult
from app.policy.rules import ALWAYS_BLOCKED_FIELDS, PolicyAction


class DataSanitizer:
    """
    Enforces the backend data filtering boundary before any data reaches AI components.
    
    CRITICAL SECURITY INVARIANTS:
    1. If the policy decision is DENY, no record data is returned (returns None).
    2. Only fields explicitly listed in `decision.permitted_fields` are extracted.
    3. Blocked and redacted attributes are completely eliminated from the sanitized payload.
    4. Input records are never mutated in place.
    """

    @classmethod
    def sanitize_records(
        cls,
        raw_records: List[Dict[str, Any]],
        decision: PolicyDecisionResult,
    ) -> Optional[List[Dict[str, Any]]]:
        if decision.action == PolicyAction.DENY:
            return None

        permitted_set = set(decision.permitted_fields)
        sanitized_records: List[Dict[str, Any]] = []

        for record in raw_records:
            sanitized_record: Dict[str, Any] = {}
            for field in decision.permitted_fields:
                if field in record:
                    sanitized_record[field] = record[field]

            # Invariant validation: verify no blocked field leaked through
            leaked_blocked = set(sanitized_record.keys()).intersection(ALWAYS_BLOCKED_FIELDS)
            if leaked_blocked:
                raise RuntimeError(
                    f"CRITICAL SECURITY INVARIANT VIOLATION: Blocked field(s) {leaked_blocked} found in sanitized record"
                )

            # Invariant validation: verify no unpermitted field exists
            leaked_unpermitted = set(sanitized_record.keys()) - permitted_set
            if leaked_unpermitted:
                raise RuntimeError(
                    f"CRITICAL SECURITY INVARIANT VIOLATION: Unpermitted field(s) {leaked_unpermitted} in sanitized record"
                )

            sanitized_records.append(sanitized_record)

        return sanitized_records
