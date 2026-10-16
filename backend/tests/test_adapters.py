import pytest
from app.adapters.base import InvalidResourceError, RecordNotFoundError
from app.adapters.mock_adapter import MockSyntheticAdapter
from app.adapters.linuxone_db2_adapter import LinuxOneDb2Adapter
from app.services.data_service import GatewayDataService
from app.policy.rules import PolicyAction, Purpose


class TestMockSyntheticAdapter:

    def test_mock_adapter_works_offline_without_ibm(self):
        """Verify the mock adapter initializes and functions 100% offline."""
        adapter = MockSyntheticAdapter()
        assert adapter.is_connected() is True

    def test_known_fictional_records_retrieved_internally(self):
        """Verify internal retrieval of synthetic records by resource and ID."""
        adapter = MockSyntheticAdapter()
        records = adapter.list_records("financial_records", limit=5)
        assert len(records) == 3
        assert records[0]["account_id"] == "ACC-FIN-1001"

        single = adapter.get_record_by_id("financial_records", "ACC-FIN-1002")
        assert single["account_id"] == "ACC-FIN-1002"
        assert single["customer_name"] == "Bob Synthetic-Sterling"

    def test_unknown_record_id_raises_record_not_found(self):
        """Verify requesting a non-existent record raises RecordNotFoundError."""
        adapter = MockSyntheticAdapter()
        with pytest.raises(RecordNotFoundError) as exc_info:
            adapter.get_record_by_id("financial_records", "NON-EXISTENT-ID-999")
        assert "not found" in str(exc_info.value).lower()

    def test_resource_isolation_enforced(self):
        """Verify invalid or unmapped resource names raise InvalidResourceError."""
        adapter = MockSyntheticAdapter()
        with pytest.raises(InvalidResourceError):
            adapter.list_records("unregistered_payroll_table")

        with pytest.raises(InvalidResourceError):
            adapter.get_record_by_id("secret_vault_table", "ACC-01")


class TestLinuxOneDb2AdapterPlaceholder:

    def test_linuxone_adapter_unimplemented_behavior(self):
        """Verify the LinuxONE/Db2 placeholder explicitly reports offline and raises NotImplementedError."""
        db2_adapter = LinuxOneDb2Adapter()
        assert db2_adapter.is_connected() is False

        with pytest.raises(NotImplementedError) as exc_info:
            db2_adapter.list_records("financial_records")
        assert "not implemented" in str(exc_info.value).lower()

        with pytest.raises(NotImplementedError):
            db2_adapter.get_record_by_id("financial_records", "ACC-01")


class TestGatewayDataService:

    def test_service_denied_policy_returns_no_data(self):
        """Verify that an unauthorized role receives no data and a safe error message."""
        service = GatewayDataService()
        result = service.query_records(
            actor_role="guest",
            purpose=Purpose.AUDIT_COMPLIANCE,
            target_resource="financial_records",
        )

        assert result.policy_decision.action == PolicyAction.DENY
        assert result.sanitized_records is None
        assert result.total_records_evaluated == 0
        assert "Access denied" in (result.error or "")

    def test_service_removes_unauthorized_fields(self):
        """Verify that authorized queries have unauthorized fields redacted before leaving the service."""
        service = GatewayDataService()
        # Financial analyst requesting financial_records for portfolio_analysis
        result = service.query_records(
            actor_role="financial_analyst",
            purpose=Purpose.PORTFOLIO_ANALYSIS,
            target_resource="financial_records",
            requested_fields=[
                "account_id",
                "account_balance",
                "ssn",
                "credit_card_number",
                "customer_name",
                "audit_notes",
            ],
        )

        assert result.policy_decision.action == PolicyAction.REDACT
        assert result.sanitized_records is not None
        assert len(result.sanitized_records) == 3

        for record in result.sanitized_records:
            # Permitted attributes
            assert "account_id" in record
            assert "account_balance" in record

            # Redacted / Blocked attributes MUST NOT be present
            assert "ssn" not in record
            assert "credit_card_number" not in record
            assert "customer_name" not in record
            assert "audit_notes" not in record

    def test_restricted_values_never_appear_in_service_response(self):
        """Verify that raw sensitive string fragments never appear in the service payload."""
        service = GatewayDataService()
        result = service.query_records(
            actor_role="data_scientist",
            purpose=Purpose.MODEL_TRAINING,
            target_resource="financial_records",
        )

        assert result.policy_decision.action in (PolicyAction.ALLOW, PolicyAction.REDACT)
        assert result.sanitized_records is not None

        # Inspect the entire payload representation
        payload_str = str(result.model_dump())
        assert "000-01-1001" not in payload_str
        assert "4111-2222" not in payload_str
        assert "Alice Fictional-Vance" not in payload_str
        assert "Bob Synthetic-Sterling" not in payload_str
        assert "rapid multi-currency" not in payload_str.lower()

    def test_service_safe_error_for_unknown_record_id(self):
        """Verify that querying a non-existent record ID returns an empty list and safe error message."""
        service = GatewayDataService()
        result = service.query_records(
            actor_role="compliance_auditor",
            purpose=Purpose.AUDIT_COMPLIANCE,
            target_resource="financial_records",
            record_id="UNKNOWN-ACC-9999",
        )

        assert result.policy_decision.action in (PolicyAction.ALLOW, PolicyAction.REDACT)
        assert result.sanitized_records == []
        assert result.error is not None
        assert "not found" in result.error.lower()
