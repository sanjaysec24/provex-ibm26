import copy
from typing import Any, Dict, List
from app.adapters.base import (
    DataSourceAdapter,
    InvalidResourceError,
    RecordNotFoundError,
)
from app.policy.rules import KNOWN_RESOURCE_SCHEMAS


# Synthetic fictional test fixtures (100% offline, zero real PII or live credentials)
SYNTHETIC_DATA_STORE: Dict[str, List[Dict[str, Any]]] = {
    "financial_records": [
        {
            "account_id": "ACC-FIN-1001",
            "customer_name": "Alice Fictional-Vance",
            "ssn": "000-01-1001",
            "credit_card_number": "4111-2222-3333-1001",
            "account_balance": 48250.75,
            "transaction_amount": 1250.00,
            "transaction_date": "2026-10-14T10:15:30Z",
            "risk_score": 0.08,
            "suspicious_flag": False,
            "audit_notes": "Tier-1 commercial account. Standard quarterly AML review passed.",
        },
        {
            "account_id": "ACC-FIN-1002",
            "customer_name": "Bob Synthetic-Sterling",
            "ssn": "000-02-1002",
            "credit_card_number": "4111-2222-3333-1002",
            "account_balance": 189200.00,
            "transaction_amount": 45000.00,
            "transaction_date": "2026-10-15T03:45:10Z",
            "risk_score": 0.82,
            "suspicious_flag": True,
            "audit_notes": "Rapid multi-currency transfer pattern flagged by real-time detector.",
        },
        {
            "account_id": "ACC-FIN-1003",
            "customer_name": "Carol Mock-Danvers",
            "ssn": "000-03-1003",
            "credit_card_number": "4111-2222-3333-1003",
            "account_balance": 9210.10,
            "transaction_amount": 89.99,
            "transaction_date": "2026-10-16T11:20:00Z",
            "risk_score": 0.02,
            "suspicious_flag": False,
            "audit_notes": "Retail checking account. Low activity, consistent payroll deposits.",
        },
    ],
    "customer_accounts": [
        {
            "account_id": "ACC-FIN-1001",
            "customer_name": "Alice Fictional-Vance",
            "ssn": "000-01-1001",
            "email": "alice.fictional@example-internal.local",
            "phone_number": "+1-555-010-1001",
            "account_type": "commercial_treasury",
            "created_at": "2024-03-15T08:00:00Z",
        },
        {
            "account_id": "ACC-FIN-1002",
            "customer_name": "Bob Synthetic-Sterling",
            "ssn": "000-02-1002",
            "email": "bob.synthetic@example-internal.local",
            "phone_number": "+1-555-010-1002",
            "account_type": "private_wealth",
            "created_at": "2023-11-20T14:30:00Z",
        },
    ],
    "transaction_logs": [
        {
            "transaction_id": "TXN-8801",
            "account_id": "ACC-FIN-1001",
            "transaction_amount": 1250.00,
            "transaction_date": "2026-10-14T10:15:30Z",
            "merchant_category": "wholesale_supplies",
            "fraud_label": "legitimate",
        },
        {
            "transaction_id": "TXN-8802",
            "account_id": "ACC-FIN-1002",
            "transaction_amount": 45000.00,
            "transaction_date": "2026-10-15T03:45:10Z",
            "merchant_category": "offshore_wire_transfer",
            "fraud_label": "flagged_investigation",
        },
    ],
}


class MockSyntheticAdapter(DataSourceAdapter):
    """
    Offline Mock Data Adapter for local development and Datathon testing.
    Provides synthetic enterprise data with zero external infrastructure dependencies.
    """

    def __init__(self, data_store: Dict[str, List[Dict[str, Any]]] = SYNTHETIC_DATA_STORE) -> None:
        self._data_store = data_store

    def is_connected(self) -> bool:
        """Always connected locally via in-memory synthetic fixtures."""
        return True

    def list_records(self, resource: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve raw synthetic records for a known resource.
        Internal use only: MUST be sanitized by policy engine before external egress.
        """
        if resource not in KNOWN_RESOURCE_SCHEMAS:
            raise InvalidResourceError(f"Resource '{resource}' is not recognized or supported.")

        records = self._data_store.get(resource, [])
        return copy.deepcopy(records[:limit])

    def get_record_by_id(self, resource: str, record_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific raw record by ID.
        Checks 'account_id' or 'transaction_id' depending on the resource schema.
        """
        if resource not in KNOWN_RESOURCE_SCHEMAS:
            raise InvalidResourceError(f"Resource '{resource}' is not recognized or supported.")

        records = self._data_store.get(resource, [])
        id_field = "transaction_id" if resource == "transaction_logs" else "account_id"

        for record in records:
            if record.get(id_field) == record_id:
                return copy.deepcopy(record)

        raise RecordNotFoundError(
            f"Record with ID '{record_id}' not found in resource '{resource}'."
        )
