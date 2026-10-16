from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    COMPLIANCE_AUDITOR = "compliance_auditor"
    FINANCIAL_ANALYST = "financial_analyst"
    DATA_SCIENTIST = "data_scientist"
    GUEST = "guest"
    ANONYMOUS = "anonymous"


class DecisionAction(str, Enum):
    ALLOW = "ALLOW"
    REDACT_AND_ALLOW = "REDACT_AND_ALLOW"
    DENY = "DENY"


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Current service health status")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the health check"
    )
    environment: str = Field(default="development", description="Current operating environment")
    data_adapter: str = Field(default="synthetic", description="Active data source adapter")
    policy_engine_active: bool = Field(default=True, description="Deterministic policy engine health")


class AuditReceipt(BaseModel):
    receipt_id: str = Field(description="Unique identifier for the audit event")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    algorithm: str = Field(default="SHA-256", description="Digest algorithm used")
    actor_role: str = Field(description="Clearance role of the requesting actor")
    action_decision: DecisionAction = Field(description="Deterministic access decision")
    total_fields: int = Field(default=0, description="Total fields evaluated")
    redacted_fields_count: int = Field(default=0, description="Number of sensitive fields filtered")
    redacted_field_names: List[str] = Field(default_factory=list, description="Names of filtered attributes")
    payload_digest: str = Field(description="Cryptographic SHA-256 digest of sanitized payload")
    receipt_digest: str = Field(description="Cryptographic SHA-256 digest of the audit receipt itself")


class GatewayQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="User or application prompt / data request")
    actor_role: UserRole = Field(default=UserRole.GUEST, description="Claimed role clearance")
    actor_id: str = Field(default="user_local", description="Identifier of the requester")
    target_resource: str = Field(default="financial_records", description="Requested data asset")


class GatewayQueryResponse(BaseModel):
    request_id: str = Field(description="Correlation ID of the request")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    actor_role: str = Field(description="Evaluated role")
    decision: DecisionAction = Field(description="Deterministic access decision")
    decision_reason: str = Field(description="Explainable policy rule rationale")
    redacted_fields: List[str] = Field(default_factory=list, description="List of stripped/masked fields")
    sanitized_payload: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Safe data passed to downstream AI (null if DENY)"
    )
    audit_receipt: AuditReceipt = Field(description="Tamper-evident audit receipt")


class ReceiptVerificationRequest(BaseModel):
    receipt: AuditReceipt = Field(description="The complete audit receipt to verify")


class ReceiptVerificationResponse(BaseModel):
    is_valid: bool = Field(description="True if cryptographic digest matches receipt contents")
    receipt_id: str = Field(description="ID of the verified receipt")
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Verification timestamp"
    )
    details: str = Field(description="Integrity verification explanation")
