import csv
import io
from typing import Any, Dict, List
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.adapters.mock_adapter import default_mock_adapter
from app.models.schemas import DatasetUploadResponse
from app.policy.rules import ALWAYS_BLOCKED_FIELDS, KNOWN_RESOURCE_SCHEMAS

router = APIRouter(prefix="/api/v1/dataset", tags=["Dataset Upload"])

MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB
MAX_ROW_COUNT = 100


def _parse_and_type_record(raw_row: Dict[str, str], resource: str) -> Dict[str, Any]:
    """Parse typed values (floats, booleans) based on known resource conventions."""
    typed_record: Dict[str, Any] = {}
    for col, val in raw_row.items():
        if col is None:
            continue
        col_clean = col.strip()
        val_clean = val.strip() if isinstance(val, str) else ""

        if col_clean in ("account_balance", "transaction_amount", "risk_score"):
            try:
                typed_record[col_clean] = float(val_clean)
            except (ValueError, TypeError):
                typed_record[col_clean] = 0.0
        elif col_clean == "suspicious_flag":
            typed_record[col_clean] = val_clean.lower() in ("true", "1", "yes")
        else:
            typed_record[col_clean] = val_clean

    return typed_record


def _create_safe_preview(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Creates a sanitized, masked preview of uploaded records.
    Never exposes raw unmasked PII, credit cards, or confidential notes.
    """
    preview: List[Dict[str, Any]] = []
    for r in records[:3]:
        safe_row: Dict[str, Any] = {}
        for k, v in r.items():
            if k in ALWAYS_BLOCKED_FIELDS:
                safe_row[k] = "***MASKED***"
            elif k == "audit_notes":
                safe_row[k] = "[CONFIDENTIAL - STORED SERVER-SIDE]"
            else:
                safe_row[k] = v
        preview.append(safe_row)
    return preview


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload synthetic enterprise CSV dataset",
    description="Validates CSV formatting, schema constraints, and loads records in-memory behind the policy engine.",
)
async def upload_csv_dataset(
    file: UploadFile = File(...),
    target_resource: str = Form("financial_records"),
) -> DatasetUploadResponse:
    # 1. Validate target resource
    if target_resource not in KNOWN_RESOURCE_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unsupported target resource '{target_resource}'. Supported: {list(KNOWN_RESOURCE_SCHEMAS.keys())}",
        )

    # 2. Validate filename extension
    filename = file.filename or "uploaded_dataset.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{filename}'. Only .csv files are supported.",
        )

    # 3. Read and validate file size
    try:
        content_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(exc)}",
        )

    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty (0 bytes).",
        )

    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of 1MB ({len(content_bytes)} bytes received).",
        )

    # 4. Validate UTF-8 encoding
    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding must be valid UTF-8. Non-UTF8 byte sequences detected.",
        )

    # 5. Parse CSV structure
    try:
        csv_stream = io.StringIO(text_content)
        reader = csv.DictReader(csv_stream)
        headers = [h.strip() for h in (reader.fieldnames or []) if h and h.strip()]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed CSV content: {str(exc)}",
        )

    if not headers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must contain a non-empty header row.",
        )

    # 6. Validate headers against resource schema (Fail closed on unknown headers)
    allowed_schema = KNOWN_RESOURCE_SCHEMAS[target_resource]
    unsupported_headers = set(headers) - allowed_schema
    if unsupported_headers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported field(s) detected: {sorted(list(unsupported_headers))}. "
                f"All columns must match the '{target_resource}' schema."
            ),
        )

    # 7. Validate required identifier column
    id_field = "transaction_id" if target_resource == "transaction_logs" else "account_id"
    if id_field not in headers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV headers must include required identifier column '{id_field}' for resource '{target_resource}'.",
        )

    # 8. Parse and validate rows
    parsed_records: List[Dict[str, Any]] = []
    record_ids: List[str] = []

    for row_idx, row in enumerate(reader, start=2):
        if not any(row.values()):
            continue  # skip completely blank rows

        record_id_val = (row.get(id_field) or "").strip()
        if not record_id_val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {row_idx}: Missing required identifier '{id_field}'.",
            )

        typed_record = _parse_and_type_record(row, target_resource)
        parsed_records.append(typed_record)
        record_ids.append(record_id_val)

        if len(parsed_records) > MAX_ROW_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row count exceeds maximum limit of {MAX_ROW_COUNT} records.",
            )

    if not parsed_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains a header row but no valid data rows.",
        )

    # 9. Ingest into in-memory mock adapter
    default_mock_adapter.load_dataset(target_resource, parsed_records, prepend=True)

    # 10. Generate safe preview (masked sensitive fields)
    preview = _create_safe_preview(parsed_records)

    return DatasetUploadResponse(
        filename=filename,
        target_resource=target_resource,
        row_count=len(parsed_records),
        detected_columns=headers,
        record_ids=record_ids,
        preview_records=preview,
        message=(
            f"Successfully ingested {len(parsed_records)} record(s) for '{target_resource}'. "
            "Raw source records are held in-memory behind the deterministic policy engine. "
            "Downstream AI queries will strictly filter unpermitted fields."
        ),
    )
