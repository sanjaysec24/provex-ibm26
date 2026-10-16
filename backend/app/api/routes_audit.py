from datetime import datetime, timezone
from fastapi import APIRouter, status

from app.audit.receipt import verify_receipt_integrity
from app.models.schemas import (
    ReceiptVerificationRequest,
    ReceiptVerificationResponse,
)

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Receipts"])


@router.post(
    "/verify",
    response_model=ReceiptVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cryptographically verify an AI Data Receipt",
    description="Recalculates canonical SHA-256 digest over receipt metadata to detect tampering.",
)
async def verify_receipt(request: ReceiptVerificationRequest) -> ReceiptVerificationResponse:
    is_valid, expected_digest, supplied_digest, details = verify_receipt_integrity(request.receipt)

    return ReceiptVerificationResponse(
        is_valid=is_valid,
        receipt_id=request.receipt.receipt_id,
        verified_at=datetime.now(timezone.utc).isoformat(),
        expected_digest=expected_digest,
        supplied_digest=supplied_digest,
        details=details,
    )
