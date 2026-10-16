import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import AuditReceipt, DecisionAction
from app.policy.engine import PolicyDecisionResult


def canonical_json(data: Any) -> str:
    """
    Serialize data into deterministic canonical JSON.
    - Keys sorted alphabetically
    - No redundant whitespace (separators=(',', ':'))
    - Strict UTF-8 compatible encoding
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_payload_digest(sanitized_payload: Optional[List[Dict[str, Any]]]) -> str:
    """
    Calculate deterministic SHA-256 digest of sanitized payload data.
    If payload is None (e.g. on DENY), hashes the canonical 'null' representation.
    """
    if sanitized_payload is None:
        raw_repr = "null"
    else:
        raw_repr = canonical_json(sanitized_payload)
    return hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()


def compute_receipt_digest(receipt_dict: Dict[str, Any]) -> str:
    """
    Calculate deterministic SHA-256 integrity digest over receipt fields.
    Crucial: Excludes 'receipt_digest' from the dictionary to avoid circular dependency.
    """
    data_to_hash = {k: v for k, v in receipt_dict.items() if k != "receipt_digest"}
    canon = canonical_json(data_to_hash)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def generate_audit_receipt(
    policy_decision: PolicyDecisionResult,
    sanitized_payload: Optional[List[Dict[str, Any]]],
    record_id: Optional[str] = None,
    algorithm: str = "SHA-256",
) -> AuditReceipt:
    """
    Constructs an immutable AI Data Receipt linking the policy decision to the sanitized payload.
    """
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    now_utc = datetime.now(timezone.utc).isoformat()
    payload_digest = compute_payload_digest(sanitized_payload)

    # Base receipt fields without receipt_digest
    receipt_data = {
        "receipt_id": receipt_id,
        "timestamp": now_utc,
        "algorithm": algorithm,
        "target_resource": policy_decision.target_resource,
        "record_id": record_id,
        "actor_role": policy_decision.actor_role,
        "purpose": policy_decision.purpose,
        "policy_id": policy_decision.policy_id,
        "action_decision": policy_decision.action.value,
        "permitted_fields": sorted(list(policy_decision.permitted_fields)),
        "redacted_fields": sorted(list(policy_decision.redacted_fields)),
        "blocked_fields": sorted(list(policy_decision.blocked_fields)),
        "payload_digest": payload_digest,
    }

    # Deterministic integrity digest
    receipt_digest = compute_receipt_digest(receipt_data)

    return AuditReceipt(
        receipt_id=receipt_id,
        timestamp=now_utc,
        algorithm=algorithm,
        target_resource=policy_decision.target_resource,
        record_id=record_id,
        actor_role=policy_decision.actor_role,
        purpose=policy_decision.purpose,
        policy_id=policy_decision.policy_id,
        action_decision=DecisionAction(policy_decision.action.value),
        permitted_fields=sorted(list(policy_decision.permitted_fields)),
        redacted_fields=sorted(list(policy_decision.redacted_fields)),
        blocked_fields=sorted(list(policy_decision.blocked_fields)),
        payload_digest=payload_digest,
        receipt_digest=receipt_digest,
    )


def verify_receipt_integrity(receipt: AuditReceipt) -> Tuple[bool, str, str, str]:
    """
    Verifies that the supplied audit receipt matches its canonical SHA-256 digest.
    
    Returns:
        (is_valid, expected_digest, supplied_digest, details_explanation)
    """
    receipt_dict = receipt.model_dump()
    expected_digest = compute_receipt_digest(receipt_dict)
    supplied_digest = receipt.receipt_digest

    is_valid = (expected_digest == supplied_digest)

    if is_valid:
        details = (
            f"Receipt integrity verified: Canonical {receipt.algorithm} digest matches expected value. "
            "Note: A plain SHA-256 digest detects metadata tampering relative to the supplied digest, "
            "but does not constitute an asymmetric digital signature or prove creator identity."
        )
    else:
        details = (
            f"Receipt integrity check FAILED: Supplied digest ({supplied_digest[:16]}...) does not match "
            f"recalculated canonical digest ({expected_digest[:16]}...). "
            "The receipt metadata, policy decision, field list, or payload hash has been tampered with."
        )

    return is_valid, expected_digest, supplied_digest, details
