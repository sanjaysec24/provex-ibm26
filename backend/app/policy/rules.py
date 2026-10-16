from enum import Enum
from typing import Dict, Set


class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    DENY = "DENY"


class Purpose(str, Enum):
    AUDIT_COMPLIANCE = "audit_compliance"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    FRAUD_DETECTION = "fraud_detection"
    MODEL_TRAINING = "model_training"
    PUBLIC_INQUIRY = "public_inquiry"


# Complete known schemas for enterprise resources
KNOWN_RESOURCE_SCHEMAS: Dict[str, Set[str]] = {
    "financial_records": {
        "account_id",
        "customer_name",
        "ssn",
        "credit_card_number",
        "account_balance",
        "transaction_amount",
        "transaction_date",
        "risk_score",
        "suspicious_flag",
        "audit_notes",
    },
    "customer_accounts": {
        "account_id",
        "customer_name",
        "ssn",
        "email",
        "phone_number",
        "account_type",
        "created_at",
    },
    "transaction_logs": {
        "transaction_id",
        "account_id",
        "transaction_amount",
        "transaction_date",
        "merchant_category",
        "fraud_label",
    },
}

# Role-based ceiling of permitted fields per resource
ROLE_RESOURCE_FIELD_CEILINGS: Dict[str, Dict[str, Set[str]]] = {
    "compliance_auditor": {
        "financial_records": {
            "account_id",
            "transaction_amount",
            "transaction_date",
            "risk_score",
            "suspicious_flag",
            "audit_notes",
        },
        "customer_accounts": {
            "account_id",
            "account_type",
            "created_at",
        },
        "transaction_logs": {
            "transaction_id",
            "account_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
            "fraud_label",
        },
    },
    "financial_analyst": {
        "financial_records": {
            "account_id",
            "account_balance",
            "transaction_amount",
            "transaction_date",
            "risk_score",
        },
        "transaction_logs": {
            "transaction_id",
            "account_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
        },
    },
    "data_scientist": {
        "financial_records": {
            "transaction_amount",
            "transaction_date",
            "risk_score",
        },
        "transaction_logs": {
            "transaction_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
            "fraud_label",
        },
    },
    # Guest and anonymous roles have ZERO permissions on enterprise resources
    "guest": {},
    "anonymous": {},
}

# Purpose-based necessity mapping (Data Minimization)
PURPOSE_NECESSARY_FIELDS: Dict[str, Dict[str, Set[str]]] = {
    "audit_compliance": {
        "financial_records": {
            "account_id",
            "suspicious_flag",
            "audit_notes",
            "transaction_date",
            "transaction_amount",
            "risk_score",
        },
        "customer_accounts": {
            "account_id",
            "account_type",
            "created_at",
        },
        "transaction_logs": {
            "transaction_id",
            "account_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
            "fraud_label",
        },
    },
    "portfolio_analysis": {
        "financial_records": {
            "account_id",
            "account_balance",
            "transaction_amount",
            "risk_score",
        },
        "transaction_logs": {
            "transaction_id",
            "account_id",
            "transaction_amount",
            "merchant_category",
        },
    },
    "fraud_detection": {
        "financial_records": {
            "account_id",
            "transaction_amount",
            "transaction_date",
            "suspicious_flag",
            "risk_score",
        },
        "transaction_logs": {
            "transaction_id",
            "account_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
            "fraud_label",
        },
    },
    "model_training": {
        "financial_records": {
            "transaction_amount",
            "transaction_date",
            "risk_score",
        },
        "transaction_logs": {
            "transaction_id",
            "transaction_amount",
            "transaction_date",
            "merchant_category",
            "fraud_label",
        },
    },
    "public_inquiry": {
        # No internal enterprise fields are necessary for public inquiries
        "financial_records": set(),
        "customer_accounts": set(),
        "transaction_logs": set(),
    },
}

# Strict globally blocked attributes that should never reach AI prompts
ALWAYS_BLOCKED_FIELDS: Set[str] = {
    "ssn",
    "credit_card_number",
    "national_id",
    "pan",
    "cvv",
    "private_key",
    "api_secret",
}
