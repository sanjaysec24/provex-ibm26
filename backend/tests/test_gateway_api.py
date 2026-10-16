import copy
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestGatewayEndpoints:

    def test_authorized_gateway_request(self):
        """Verify successful processing of an authorized gateway request."""
        payload = {
            "query": "Analyze quarterly portfolio transactions for commercial accounts",
            "actor_role": "financial_analyst",
            "purpose": "portfolio_analysis",
            "target_resource": "financial_records",
            "requested_fields": ["account_id", "account_balance", "transaction_amount", "risk_score"],
        }
        response = client.post("/api/v1/gateway/process", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "ALLOW"
        assert data["sanitized_payload"] is not None
        assert len(data["sanitized_payload"]) > 0
        assert data["audit_receipt"]["receipt_id"].startswith("rcpt_")
        assert data["audit_receipt"]["action_decision"] == "ALLOW"
        assert len(data["audit_receipt"]["receipt_digest"]) == 64

    def test_unauthorized_gateway_request_denial(self):
        """Verify that an unauthorized role (e.g. guest) is safely denied with zero data exposed."""
        payload = {
            "query": "Fetch all accounts and balances",
            "actor_role": "guest",
            "purpose": "audit_compliance",
            "target_resource": "financial_records",
        }
        response = client.post("/api/v1/gateway/process", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "DENY"
        assert data["sanitized_payload"] is None
        assert data["audit_receipt"]["action_decision"] == "DENY"
        assert "Access denied" in data["decision_reason"]

    def test_excessive_access_data_minimization(self):
        """Verify that requesting excessive or restricted fields triggers REDACT and strips them."""
        payload = {
            "query": "Provide full records including SSN and credit card",
            "actor_role": "financial_analyst",
            "purpose": "portfolio_analysis",
            "target_resource": "financial_records",
            "requested_fields": [
                "account_id",
                "account_balance",
                "ssn",
                "credit_card_number",
                "customer_name",
                "audit_notes",
            ],
        }
        response = client.post("/api/v1/gateway/process", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "REDACT"
        assert data["sanitized_payload"] is not None

        # Verify only minimization fields remain
        for record in data["sanitized_payload"]:
            assert "account_id" in record
            assert "account_balance" in record
            assert "ssn" not in record
            assert "credit_card_number" not in record
            assert "customer_name" not in record
            assert "audit_notes" not in record

    def test_no_blocked_values_in_response_or_receipt(self):
        """Verify that raw sensitive values never appear anywhere in the HTTP response."""
        payload = {
            "query": "Export financial data",
            "actor_role": "financial_analyst",
            "purpose": "portfolio_analysis",
            "target_resource": "financial_records",
        }
        response = client.post("/api/v1/gateway/process", json=payload)
        assert response.status_code == 200
        raw_text = response.text

        # Fictional sensitive fragments from mock store
        assert "000-01-1001" not in raw_text
        assert "000-02-1002" not in raw_text
        assert "4111-2222" not in raw_text
        assert "Alice Fictional-Vance" not in raw_text
        assert "rapid multi-currency" not in raw_text.lower()

    def test_adapter_unknown_record_id_handling(self):
        """Verify safe error response when querying a non-existent record ID."""
        payload = {
            "query": "Retrieve specific account",
            "actor_role": "compliance_auditor",
            "purpose": "audit_compliance",
            "target_resource": "financial_records",
            "record_id": "ACC-DOES-NOT-EXIST-404",
        }
        response = client.post("/api/v1/gateway/process", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["sanitized_payload"] == []
        assert "not found" in data["decision_reason"].lower()

    def test_invalid_request_payload_validation(self):
        """Verify validation errors for empty query or malformed request."""
        # Empty whitespace query
        bad_query_res = client.post(
            "/api/v1/gateway/process",
            json={"query": "   ", "actor_role": "guest"},
        )
        assert bad_query_res.status_code == 400
        assert "cannot be empty" in bad_query_res.text.lower()

        # Missing required query field
        missing_query_res = client.post(
            "/api/v1/gateway/process",
            json={"actor_role": "guest"},
        )
        assert missing_query_res.status_code == 422


class TestAuditReceiptVerification:

    def test_receipt_generation_and_valid_verification(self):
        """Verify that a legitimate receipt produced by the gateway passes verification."""
        # 1. Generate receipt via gateway
        gateway_res = client.post(
            "/api/v1/gateway/process",
            json={
                "query": "Audit suspicious transactions",
                "actor_role": "compliance_auditor",
                "purpose": "audit_compliance",
                "target_resource": "financial_records",
            },
        )
        assert gateway_res.status_code == 200
        receipt = gateway_res.json()["audit_receipt"]

        # 2. Verify receipt
        verify_res = client.post(
            "/api/v1/audit/verify",
            json={"receipt": receipt},
        )
        assert verify_res.status_code == 200
        verify_data = verify_res.json()

        assert verify_data["is_valid"] is True
        assert verify_data["receipt_id"] == receipt["receipt_id"]
        assert verify_data["expected_digest"] == receipt["receipt_digest"]
        assert "integrity verified" in verify_data["details"].lower()

    def test_tampered_receipt_rejected(self):
        """Verify that modifying any parameter of the receipt breaks verification."""
        gateway_res = client.post(
            "/api/v1/gateway/process",
            json={
                "query": "Audit transactions",
                "actor_role": "compliance_auditor",
                "purpose": "audit_compliance",
                "target_resource": "financial_records",
            },
        )
        original_receipt = gateway_res.json()["audit_receipt"]

        # Tamper 1: Alter timestamp
        tampered_time = copy.deepcopy(original_receipt)
        tampered_time["timestamp"] = "1999-01-01T00:00:00Z"
        res_time = client.post("/api/v1/audit/verify", json={"receipt": tampered_time})
        assert res_time.status_code == 200
        assert res_time.json()["is_valid"] is False

        # Tamper 2: Alter decision from REDACT to ALLOW
        tampered_decision = copy.deepcopy(original_receipt)
        tampered_decision["action_decision"] = "ALLOW"
        res_dec = client.post("/api/v1/audit/verify", json={"receipt": tampered_decision})
        assert res_dec.status_code == 200
        assert res_dec.json()["is_valid"] is False

        # Tamper 3: Inject unpermitted field into permitted_fields list
        tampered_fields = copy.deepcopy(original_receipt)
        tampered_fields["permitted_fields"].append("ssn")
        res_fields = client.post("/api/v1/audit/verify", json={"receipt": tampered_fields})
        assert res_fields.status_code == 200
        assert res_fields.json()["is_valid"] is False

        # Tamper 4: Alter payload digest
        tampered_digest = copy.deepcopy(original_receipt)
        tampered_digest["payload_digest"] = "0" * 64
        res_dig = client.post("/api/v1/audit/verify", json={"receipt": tampered_digest})
        assert res_dig.status_code == 200
        assert res_dig.json()["is_valid"] is False
