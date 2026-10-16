import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status

from app.audit.receipt import generate_audit_receipt
from app.models.schemas import (
    DecisionAction,
    GatewayQueryRequest,
    GatewayQueryResponse,
)
from app.services.data_service import GatewayDataService

router = APIRouter(prefix="/api/v1/gateway", tags=["Gateway"])
data_service = GatewayDataService()


@router.post(
    "/process",
    response_model=GatewayQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Process prompt or data request through deterministic security policy",
    description="Evaluates clearance, enforces data minimization, filters sensitive attributes, and emits an AI Data Receipt.",
)
async def process_gateway_request(request: GatewayQueryRequest) -> GatewayQueryResponse:
    # 1. Validation check for query string
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty or whitespace only.",
        )

    # 2. Invoke GatewayDataService (Policy Engine -> Sanitizer -> Safe Data)
    service_result = data_service.query_records(
        actor_role=request.actor_role.value,
        purpose=request.purpose,
        target_resource=request.target_resource,
        record_id=request.record_id,
        requested_fields=request.requested_fields,
        untrusted_prompt=clean_query,
        is_authenticated=True,
    )

    policy_dec = service_result.policy_decision

    # 3. Generate deterministic AI Data Receipt
    receipt = generate_audit_receipt(
        policy_decision=policy_dec,
        sanitized_payload=service_result.sanitized_records,
        record_id=request.record_id,
    )

    # 4. Construct explainable response
    action_decision = DecisionAction(policy_dec.action.value)
    now_utc = datetime.now(timezone.utc).isoformat()
    req_id = f"req_{uuid.uuid4().hex[:12]}"

    return GatewayQueryResponse(
        request_id=req_id,
        timestamp=now_utc,
        actor_role=policy_dec.actor_role,
        purpose=policy_dec.purpose,
        target_resource=policy_dec.target_resource,
        decision=action_decision,
        decision_reason=policy_dec.reason if not service_result.error else f"{policy_dec.reason} ({service_result.error})",
        permitted_fields=policy_dec.permitted_fields,
        redacted_fields=policy_dec.redacted_fields,
        sanitized_payload=service_result.sanitized_records,
        audit_receipt=receipt,
    )
