import logging
import uuid
from typing import List, Optional, Set
from pydantic import BaseModel, Field

from app.policy.rules import (
    ALWAYS_BLOCKED_FIELDS,
    KNOWN_RESOURCE_SCHEMAS,
    PURPOSE_NECESSARY_FIELDS,
    ROLE_RESOURCE_FIELD_CEILINGS,
    PolicyAction,
)

logger = logging.getLogger("provex.policy")


class PolicyDecisionResult(BaseModel):
    """Structured policy outcome containing only metadata and field names."""
    policy_id: str = Field(description="Unique evaluation identifier")
    action: PolicyAction = Field(description="Deterministic access outcome: ALLOW, REDACT, or DENY")
    reason: str = Field(description="Explainable decision rationale")
    actor_role: str = Field(description="Evaluated actor role")
    purpose: str = Field(description="Evaluated access purpose")
    target_resource: str = Field(description="Evaluated resource")
    permitted_fields: List[str] = Field(default_factory=list, description="Fields allowed and necessary")
    redacted_fields: List[str] = Field(default_factory=list, description="Fields denied by policy or minimization")
    blocked_fields: List[str] = Field(default_factory=list, description="Strictly restricted fields (PII/secrets)")


class DeterministicPolicyEngine:
    """
    Deterministic Zero-Trust Policy Engine for PROVEX.
    
    CRITICAL SECURITY INVARIANTS:
    1. Deterministic pure-Python evaluation - NO LLM or probabilistic model is used for access control.
    2. Fail-Closed - Unknown roles, unknown fields, invalid purposes, missing authorization,
       or evaluation anomalies immediately return DENY.
    3. Untrusted Prompt Invariant - User prompt strings are never inspected for authorization grants.
    4. Data Minimization - Permitted fields must be BOTH authorized for the role AND necessary for the purpose.
    5. Blocked Field Invariant - SSN, PAN, and credentials can never be granted under any circumstance.
    """

    POLICY_VERSION = "2026.1-ibm-z"

    @classmethod
    def evaluate(
        cls,
        actor_role: str,
        purpose: str,
        target_resource: str,
        requested_fields: Optional[List[str]] = None,
        untrusted_prompt: Optional[str] = None,  # Intentionally ignored for authorization
        is_authenticated: bool = True,
    ) -> PolicyDecisionResult:
        policy_id = f"POL-{uuid.uuid4().hex[:12].upper()}"

        try:
            # 1. Fail closed on unauthenticated or missing authorization
            if not is_authenticated:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.DENY,
                    reason="Fail-closed: Requester is unauthenticated or authorization token is invalid",
                    actor_role=str(actor_role),
                    purpose=str(purpose),
                    target_resource=str(target_resource),
                )

            # 2. Validate known actor role
            if actor_role not in ROLE_RESOURCE_FIELD_CEILINGS:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.DENY,
                    reason=f"Fail-closed: Unknown or unmapped actor role '{actor_role}'",
                    actor_role=str(actor_role),
                    purpose=str(purpose),
                    target_resource=str(target_resource),
                )

            # 3. Validate known target resource
            if target_resource not in KNOWN_RESOURCE_SCHEMAS:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.DENY,
                    reason=f"Fail-closed: Unknown or unmapped target resource '{target_resource}'",
                    actor_role=actor_role,
                    purpose=str(purpose),
                    target_resource=str(target_resource),
                )

            # 4. Validate known purpose
            if purpose not in PURPOSE_NECESSARY_FIELDS:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.DENY,
                    reason=f"Fail-closed: Invalid or unregistered purpose '{purpose}'",
                    actor_role=actor_role,
                    purpose=str(purpose),
                    target_resource=target_resource,
                )

            known_schema = KNOWN_RESOURCE_SCHEMAS[target_resource]

            # 5. Determine candidate fields to evaluate
            if requested_fields is None:
                candidate_fields: Set[str] = set(known_schema)
            else:
                candidate_fields = set(requested_fields)
                # Fail closed if any requested field is not part of the known schema
                unknown_fields = candidate_fields - known_schema
                if unknown_fields:
                    return PolicyDecisionResult(
                        policy_id=policy_id,
                        action=PolicyAction.DENY,
                        reason=f"Fail-closed: Unknown field(s) requested: {sorted(list(unknown_fields))}",
                        actor_role=actor_role,
                        purpose=purpose,
                        target_resource=target_resource,
                        blocked_fields=sorted(list(unknown_fields)),
                    )

            # 6. Retrieve role permissions ceiling for resource
            role_allowed = ROLE_RESOURCE_FIELD_CEILINGS[actor_role].get(target_resource, set())

            # 7. Retrieve purpose necessity for resource (Data Minimization)
            purpose_needed = PURPOSE_NECESSARY_FIELDS[purpose].get(target_resource, set())

            # 8. Dual intersection: Field must be BOTH authorized for role AND necessary for purpose
            authorized_and_necessary = role_allowed.intersection(purpose_needed)

            # 9. Strictly strip globally blocked sensitive attributes
            effective_permitted = authorized_and_necessary - ALWAYS_BLOCKED_FIELDS

            # 10. Compute final permitted, redacted, and blocked field sets
            final_permitted_set = candidate_fields.intersection(effective_permitted)
            final_redacted_set = candidate_fields - final_permitted_set

            # Identify which redacted fields were strictly blocked (PII/secrets)
            explicitly_blocked = candidate_fields.intersection(ALWAYS_BLOCKED_FIELDS)

            permitted_list = sorted(list(final_permitted_set))
            redacted_list = sorted(list(final_redacted_set))
            blocked_list = sorted(list(explicitly_blocked))

            # 11. Determine policy outcome action
            if not permitted_list:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.DENY,
                    reason=(
                        f"Access denied: Role '{actor_role}' has no authorized, necessary fields "
                        f"for resource '{target_resource}' under purpose '{purpose}'"
                    ),
                    actor_role=actor_role,
                    purpose=purpose,
                    target_resource=target_resource,
                    permitted_fields=[],
                    redacted_fields=redacted_list,
                    blocked_fields=blocked_list,
                )

            if not redacted_list:
                return PolicyDecisionResult(
                    policy_id=policy_id,
                    action=PolicyAction.ALLOW,
                    reason=(
                        f"Access granted: All {len(permitted_list)} requested fields are authorized for role "
                        f"'{actor_role}' and necessary for purpose '{purpose}'"
                    ),
                    actor_role=actor_role,
                    purpose=purpose,
                    target_resource=target_resource,
                    permitted_fields=permitted_list,
                    redacted_fields=[],
                    blocked_fields=[],
                )

            # Partial access: permitted subset allowed, unauthorized/unnecessary fields redacted
            reasons = []
            if blocked_list:
                reasons.append(f"blocked sensitive attributes {blocked_list}")
            unnecessary_count = len(redacted_list) - len(blocked_list)
            if unnecessary_count > 0:
                reasons.append(f"{unnecessary_count} fields pruned by data minimization")

            reason_str = "; ".join(reasons) if reasons else f"{len(redacted_list)} fields pruned by policy"

            return PolicyDecisionResult(
                policy_id=policy_id,
                action=PolicyAction.REDACT,
                reason=f"Partial access granted: {reason_str}",
                actor_role=actor_role,
                purpose=purpose,
                target_resource=target_resource,
                permitted_fields=permitted_list,
                redacted_fields=redacted_list,
                blocked_fields=blocked_list,
            )

        except Exception as exc:
            logger.exception("Unexpected error during policy evaluation: %s", exc)
            return PolicyDecisionResult(
                policy_id=policy_id,
                action=PolicyAction.DENY,
                reason=f"Fail-closed: Policy evaluation error ({exc.__class__.__name__})",
                actor_role=str(actor_role),
                purpose=str(purpose),
                target_resource=str(target_resource),
            )
