import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_VALID_CSV = """account_id,customer_name,ssn,credit_card_number,account_balance,transaction_amount,transaction_date,risk_score,suspicious_flag,audit_notes
ACC-UPL-001,Diana Upload-Prince,000-99-0001,4111-9999-0000-0001,75000.50,1500.00,2026-10-17T12:00:00Z,0.05,false,Verified payroll commercial client.
ACC-UPL-002,Bruce Upload-Wayne,000-99-0002,4111-9999-0000-0002,250000.00,80000.00,2026-10-17T14:30:00Z,0.78,true,Flagged for international wire pattern.
"""

SAMPLE_INVALID_FIELDS_CSV = """account_id,customer_name,ssn,arbitrary_injected_column,another_unknown_field
ACC-ERR-001,Bad Actor,000-00-0000,malicious_payload,extra_data
"""

SAMPLE_MISSING_ID_CSV = """customer_name,ssn,account_balance,transaction_amount
Incomplete Record,000-11-2222,500.0,25.0
"""


class TestDatasetUploadAndWorkflow:

    def test_successful_csv_dataset_upload(self):
        """Verify successful upload, parsing, in-memory loading, and safe preview generation."""
        csv_file = io.BytesIO(SAMPLE_VALID_CSV.encode("utf-8"))
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("commercial_accounts.csv", csv_file, "text/csv")},
            data={"target_resource": "financial_records"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "commercial_accounts.csv"
        assert data["target_resource"] == "financial_records"
        assert data["row_count"] == 2
        assert "account_id" in data["detected_columns"]
        assert "ssn" in data["detected_columns"]
        assert data["record_ids"] == ["ACC-UPL-001", "ACC-UPL-002"]

        # Verify preview records are safely masked
        assert len(data["preview_records"]) == 2
        for preview_row in data["preview_records"]:
            assert preview_row["ssn"] == "***MASKED***"
            assert preview_row["credit_card_number"] == "***MASKED***"
            assert "[CONFIDENTIAL" in preview_row["audit_notes"]
            assert "000-99-0001" not in str(preview_row)

    def test_uploaded_record_query_through_security_gateway(self):
        """
        Verify that uploaded records can be queried through the gateway,
        subject to policy evaluation and pre-AI redaction.
        """
        # Upload dataset first
        csv_file = io.BytesIO(SAMPLE_VALID_CSV.encode("utf-8"))
        client.post(
            "/api/v1/dataset/upload",
            files={"file": ("commercial_accounts.csv", csv_file, "text/csv")},
            data={"target_resource": "financial_records"},
        )

        # Query uploaded record as financial_analyst
        response = client.post(
            "/api/v1/gateway/process",
            json={
                "query": "Evaluate liquidity for newly uploaded account ACC-UPL-001",
                "actor_role": "financial_analyst",
                "purpose": "portfolio_analysis",
                "target_resource": "financial_records",
                "record_id": "ACC-UPL-001",
                "requested_fields": [
                    "account_id",
                    "account_balance",
                    "ssn",
                    "credit_card_number",
                    "transaction_amount",
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "REDACT"
        assert data["sanitized_payload"] is not None
        assert len(data["sanitized_payload"]) == 1

        record = data["sanitized_payload"][0]
        assert record["account_id"] == "ACC-UPL-001"
        assert record["account_balance"] == 75000.50
        assert "ssn" not in record
        assert "credit_card_number" not in record

        # Verify receipt covers the uploaded record
        receipt = data["audit_receipt"]
        assert receipt["record_id"] == "ACC-UPL-001"
        assert receipt["action_decision"] == "REDACT"

    def test_uploaded_record_denied_for_unauthorized_role(self):
        """Verify that an unauthorized role querying an uploaded record is denied with zero data returned."""
        response = client.post(
            "/api/v1/gateway/process",
            json={
                "query": "Extract uploaded confidential data",
                "actor_role": "guest",
                "purpose": "audit_compliance",
                "target_resource": "financial_records",
                "record_id": "ACC-UPL-002",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "DENY"
        assert data["sanitized_payload"] is None
        assert data["audit_receipt"]["action_decision"] == "DENY"

    def test_receipt_verification_for_uploaded_query(self):
        """Verify audit receipt integrity for a gateway query over an uploaded record."""
        gateway_res = client.post(
            "/api/v1/gateway/process",
            json={
                "query": "Audit suspicious anomaly on ACC-UPL-002",
                "actor_role": "compliance_auditor",
                "purpose": "audit_compliance",
                "target_resource": "financial_records",
                "record_id": "ACC-UPL-002",
            },
        )
        assert gateway_res.status_code == 200
        receipt = gateway_res.json()["audit_receipt"]

        verify_res = client.post("/api/v1/audit/verify", json={"receipt": receipt})
        assert verify_res.status_code == 200
        assert verify_res.json()["is_valid"] is True

    def test_empty_file_upload_rejected(self):
        """Verify 0-byte file upload returns 400 Bad Request."""
        empty_file = io.BytesIO(b"")
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("empty.csv", empty_file, "text/csv")},
            data={"target_resource": "financial_records"},
        )
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    def test_unsupported_file_extension_rejected(self):
        """Verify non-CSV file extension returns 400 Bad Request."""
        text_file = io.BytesIO(b"some content")
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("data.txt", text_file, "text/plain")},
            data={"target_resource": "financial_records"},
        )
        assert response.status_code == 400
        assert "only .csv" in response.text.lower()

    def test_unsupported_fields_rejected_fail_closed(self):
        """Verify upload containing unmapped/unknown columns fails closed with 400 Bad Request."""
        csv_file = io.BytesIO(SAMPLE_INVALID_FIELDS_CSV.encode("utf-8"))
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("corrupt.csv", csv_file, "text/csv")},
            data={"target_resource": "financial_records"},
        )
        assert response.status_code == 400
        assert "unsupported field" in response.text.lower()
        assert "arbitrary_injected_column" in response.text

    def test_missing_identifier_column_rejected(self):
        """Verify upload missing primary identifier column returns 400 Bad Request."""
        csv_file = io.BytesIO(SAMPLE_MISSING_ID_CSV.encode("utf-8"))
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("no_id.csv", csv_file, "text/csv")},
            data={"target_resource": "financial_records"},
        )
        assert response.status_code == 400
        assert "must include required identifier" in response.text.lower()

    def test_invalid_target_resource_rejected(self):
        """Verify upload specifying non-existent resource returns 400 Bad Request."""
        csv_file = io.BytesIO(SAMPLE_VALID_CSV.encode("utf-8"))
        response = client.post(
            "/api/v1/dataset/upload",
            files={"file": ("valid.csv", csv_file, "text/csv")},
            data={"target_resource": "unknown_shadow_database"},
        )
        assert response.status_code == 400
        assert "unknown or unsupported target resource" in response.text.lower()
