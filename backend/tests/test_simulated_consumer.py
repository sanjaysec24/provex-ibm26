from app.models.schemas import DecisionAction
from app.services.simulated_consumer import DeterministicAiConsumer


class TestDeterministicAiConsumer:

    def test_consumer_halts_on_denied_decision(self):
        """Verify simulated consumer refuses to answer when gateway decision is DENY."""
        result = DeterministicAiConsumer.analyze(
            decision=DecisionAction.DENY,
            permitted_fields=[],
            sanitized_payload=None,
            purpose="audit_compliance",
            target_resource="financial_records",
        )
        assert result.can_answer is False
        assert "BLOCKED" in result.status_label
        assert "Zero source records reached" in result.summary
        assert result.metrics == {}

    def test_consumer_synthesizes_portfolio_analysis(self):
        """Verify valid analysis generation using approved portfolio fields."""
        sanitized = [
            {"account_id": "ACC-01", "account_balance": 1000.0, "transaction_amount": 50.0, "risk_score": 0.1},
            {"account_id": "ACC-02", "account_balance": 2000.0, "transaction_amount": 150.0, "risk_score": 0.2},
        ]
        result = DeterministicAiConsumer.analyze(
            decision=DecisionAction.REDACT,
            permitted_fields=["account_id", "account_balance", "transaction_amount", "risk_score"],
            sanitized_payload=sanitized,
            purpose="portfolio_analysis",
            target_resource="financial_records",
        )
        assert result.can_answer is True
        assert result.metrics["total_aggregate_balance"] == 3000.0
        assert result.metrics["total_transaction_volume"] == 200.0
        assert "PII, full account numbers" in result.data_minimization_notice

    def test_consumer_declares_insufficient_data(self):
        """Verify consumer explicitly states insufficient data when required metrics were redacted."""
        # Only account_id permitted, no financial numbers
        sanitized = [{"account_id": "ACC-01"}]
        result = DeterministicAiConsumer.analyze(
            decision=DecisionAction.REDACT,
            permitted_fields=["account_id"],
            sanitized_payload=sanitized,
            purpose="portfolio_analysis",
            target_resource="financial_records",
        )
        assert result.can_answer is False
        assert "INSUFFICIENT DATA" in result.status_label
        assert "Cannot generate portfolio analysis" in result.summary
