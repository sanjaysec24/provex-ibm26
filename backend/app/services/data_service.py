import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.adapters.base import DataSourceAdapter, InvalidResourceError, RecordNotFoundError
from app.adapters.mock_adapter import MockSyntheticAdapter, default_mock_adapter
from app.policy.data_sanitizer import DataSanitizer
from app.policy.engine import DeterministicPolicyEngine, PolicyDecisionResult
from app.policy.rules import PolicyAction

logger = logging.getLogger("provex.service")


class SafeServiceResult(BaseModel):
    """
    Sanitized output contract for gateway data access.
    Guarantees raw unredacted data is never returned to callers or AI models.
    """
    policy_decision: PolicyDecisionResult = Field(description="Deterministic policy outcome")
    sanitized_records: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Safe data containing only permitted attributes (None on DENY)"
    )
    total_records_evaluated: int = Field(default=0, description="Count of candidate records processed")
    error: Optional[str] = Field(default=None, description="Safe error message if operation failed")


class GatewayDataService:
    """
    Coordinates internal data retrieval with deterministic policy enforcement
    and pre-AI redaction filtering.
    
    CRITICAL SECURITY INVARIANTS:
    1. Pre-fetch Policy Evaluation: Policy engine is evaluated BEFORE any data is returned.
    2. Fail-Closed On Deny: If policy outcome is DENY, raw data is never fetched or returned.
    3. Mandatory Sanitization: All raw records fetched internally are filtered by DataSanitizer.
    4. Safe Error Propagation: Missing or invalid record requests return safe error responses.
    """

    def __init__(self, adapter: Optional[DataSourceAdapter] = None) -> None:
        self.adapter = adapter or default_mock_adapter

    def query_records(
        self,
        actor_role: str,
        purpose: str,
        target_resource: str,
        record_id: Optional[str] = None,
        requested_fields: Optional[List[str]] = None,
        untrusted_prompt: Optional[str] = None,
        is_authenticated: bool = True,
        limit: int = 10,
    ) -> SafeServiceResult:
        # 1. Deterministic policy evaluation (First Security Gate)
        decision = DeterministicPolicyEngine.evaluate(
            actor_role=actor_role,
            purpose=purpose,
            target_resource=target_resource,
            requested_fields=requested_fields,
            untrusted_prompt=untrusted_prompt,
            is_authenticated=is_authenticated,
        )

        # 2. Strict Fail-Closed if policy denies
        if decision.action == PolicyAction.DENY:
            return SafeServiceResult(
                policy_decision=decision,
                sanitized_records=None,
                total_records_evaluated=0,
                error=decision.reason,
            )

        # 3. Internal retrieval from adapter (Internal boundary only)
        raw_records: List[Dict[str, Any]] = []
        try:
            if record_id:
                single_record = self.adapter.get_record_by_id(target_resource, record_id)
                raw_records = [single_record]
            else:
                raw_records = self.adapter.list_records(target_resource, limit=limit)
        except RecordNotFoundError as rnf:
            return SafeServiceResult(
                policy_decision=decision,
                sanitized_records=[],
                total_records_evaluated=0,
                error=str(rnf),
            )
        except InvalidResourceError as ire:
            return SafeServiceResult(
                policy_decision=decision,
                sanitized_records=None,
                total_records_evaluated=0,
                error=str(ire),
            )
        except Exception as exc:
            logger.exception("Unexpected error in adapter retrieval: %s", exc)
            return SafeServiceResult(
                policy_decision=decision,
                sanitized_records=None,
                total_records_evaluated=0,
                error=f"Internal data retrieval error: {exc.__class__.__name__}",
            )

        # 4. Mandatory data redaction before external exposure
        sanitized = DataSanitizer.sanitize_records(raw_records, decision)

        return SafeServiceResult(
            policy_decision=decision,
            sanitized_records=sanitized,
            total_records_evaluated=len(raw_records),
            error=None,
        )
