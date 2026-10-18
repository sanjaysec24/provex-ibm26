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
    REDACT = "REDACT"
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
    """
    Tamper-evident AI Data Receipt.
    
    Contains strictly policy metadata and cryptographic digests.
    Never contains raw blocked values, credentials, or unprotected PII.
    """
    receipt_id: str = Field(description="Unique identifier for the audit event")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    algorithm: str = Field(default="SHA-256", description="Digest algorithm used")
    target_resource: str = Field(description="Target enterprise data asset")
    record_id: Optional[str] = Field(default=None, description="Queried record ID if single-record request")
    actor_role: str = Field(description="Evaluated clearance role")
    purpose: str = Field(description="Stated data access purpose")
    policy_id: str = Field(description="Deterministic policy identifier")
    action_decision: DecisionAction = Field(description="Deterministic access outcome: ALLOW, REDACT, or DENY")
    permitted_fields: List[str] = Field(default_factory=list, description="Fields approved for downstream AI ingestion")
    redacted_fields: List[str] = Field(default_factory=list, description="Fields pruned by policy or data minimization")
    blocked_fields: List[str] = Field(default_factory=list, description="Strictly restricted fields (PII/secrets)")
    payload_digest: str = Field(description="SHA-256 digest of sanitized output (or 'null' on DENY)")
    receipt_digest: str = Field(description="Canonical SHA-256 digest over receipt metadata")


class GatewayQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="User or application prompt / data request")
    actor_role: UserRole = Field(default=UserRole.GUEST, description="Claimed role clearance")
    purpose: str = Field(default="portfolio_analysis", description="Stated business/operational purpose")
    actor_id: str = Field(default="user_local", description="Identifier of the requester")
    target_resource: str = Field(default="financial_records", description="Requested data asset")
    record_id: Optional[str] = Field(default=None, description="Optional single record identifier")
    requested_fields: Optional[List[str]] = Field(default=None, description="Specific columns requested")


class GatewayQueryResponse(BaseModel):
    request_id: str = Field(description="Correlation ID of the request")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    actor_role: str = Field(description="Evaluated role")
    purpose: str = Field(description="Evaluated purpose")
    target_resource: str = Field(description="Target resource")
    decision: DecisionAction = Field(description="Deterministic access decision")
    decision_reason: str = Field(description="Explainable policy rule rationale")
    permitted_fields: List[str] = Field(default_factory=list, description="List of permitted field names")
    redacted_fields: List[str] = Field(default_factory=list, description="List of stripped/masked fields")
    sanitized_payload: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Safe data passed to downstream AI (None if DENY)"
    )
    audit_receipt: AuditReceipt = Field(description="Tamper-evident audit receipt")
    auth_disclaimer: str = Field(
        default="PROTOTYPE ASSUMPTION: Client-provided role is for demonstration and policy testing; production deployments require authenticated token validation.",
        description="Notice regarding demo identity assumption"
    )


class ReceiptVerificationRequest(BaseModel):
    receipt: AuditReceipt = Field(description="The complete audit receipt to verify")


class ReceiptVerificationResponse(BaseModel):
    is_valid: bool = Field(description="True if cryptographic digest matches canonical receipt contents")
    receipt_id: str = Field(description="ID of the verified receipt")
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Verification timestamp"
    )
    expected_digest: str = Field(description="Recalculated canonical digest")
    supplied_digest: str = Field(description="Digest supplied on receipt")
    details: str = Field(description="Integrity verification explanation and cryptographic caveat")


class DatasetUploadResponse(BaseModel):
    filename: str = Field(description="Uploaded CSV filename")
    target_resource: str = Field(description="Enterprise resource schema mapped")
    row_count: int = Field(description="Number of records parsed and loaded")
    detected_columns: List[str] = Field(description="Column headers discovered in CSV")
    record_ids: List[str] = Field(description="List of primary record identifiers loaded")
    preview_records: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Safe sample preview with sensitive fields masked"
    )
    message: str = Field(description="Status confirmation and security note")

