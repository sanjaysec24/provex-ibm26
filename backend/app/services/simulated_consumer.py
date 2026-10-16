from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.schemas import DecisionAction


class SimulatedAnalysisResult(BaseModel):
    can_answer: bool = Field(description="True if permitted fields are sufficient to compute analysis")
    status_label: str = Field(description="Display status badge")
    summary: str = Field(description="Executive narrative synthesized strictly from permitted fields")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Key metrics extracted from sanitized payload")
    data_minimization_notice: str = Field(description="Explicit note of attributes excluded from AI ingestion")
    disclaimer: str = Field(
        default="DETERMINISTIC SIMULATION: Evaluates approved fields only. No external LLM or AI API invoked.",
        description="Notice confirming simulation mode"
    )


class DeterministicAiConsumer:
    """
    Deterministic simulated AI consumer for PROVEX demonstrations.
    
    CRITICAL SECURITY INVARIANTS:
    1. Consumes ONLY sanitized payload from the gateway. Never accesses raw source records.
    2. If gateway decision is DENY or payload is empty, halts immediately.
    3. If approved fields are insufficient for the stated purpose, refuses to guess or hallucinate.
    4. Input user prompts cannot override policy boundaries or force revelation of blocked fields.
    """

    @classmethod
    def analyze(
        cls,
        decision: DecisionAction,
        permitted_fields: List[str],
        sanitized_payload: Optional[List[Dict[str, Any]]],
        purpose: str,
        target_resource: str,
    ) -> SimulatedAnalysisResult:
        # 1. Immediate halt on DENY or missing data
        if decision == DecisionAction.DENY or not sanitized_payload:
            return SimulatedAnalysisResult(
                can_answer=False,
                status_label="BLOCKED: Access Denied",
                summary=(
                    "Simulated AI ingestion halted. The deterministic security gateway denied access to "
                    f"resource '{target_resource}'. Zero source records reached downstream processing."
                ),
                metrics={},
                data_minimization_notice="Zero fields transmitted to simulated consumer.",
            )

        permitted_set = set(permitted_fields)

        # 2. Financial / Portfolio Analysis
        if purpose == "portfolio_analysis":
            has_balance = "account_balance" in permitted_set
            has_amount = "transaction_amount" in permitted_set
            has_risk = "risk_score" in permitted_set

            if not (has_balance or has_amount):
                return SimulatedAnalysisResult(
                    can_answer=False,
                    status_label="INSUFFICIENT DATA",
                    summary="Cannot generate portfolio analysis: Financial figures (balance/amount) were not approved by policy.",
                    metrics={},
                    data_minimization_notice="Account balances and transaction amounts were pruned by data minimization.",
                )

            total_balance = sum(float(r.get("account_balance", 0.0)) for r in sanitized_payload if "account_balance" in r)
            total_transacted = sum(float(r.get("transaction_amount", 0.0)) for r in sanitized_payload if "transaction_amount" in r)
            avg_risk = (
                sum(float(r.get("risk_score", 0.0)) for r in sanitized_payload if "risk_score" in r) / len(sanitized_payload)
                if has_risk and sanitized_payload else None
            )

            metrics = {
                "records_evaluated": len(sanitized_payload),
                "total_aggregate_balance": round(total_balance, 2) if has_balance else "Excluded",
                "total_transaction_volume": round(total_transacted, 2) if has_amount else "Excluded",
                "average_risk_score": round(avg_risk, 3) if avg_risk is not None else "Excluded",
            }

            summary = (
                f"Portfolio analysis completed across {len(sanitized_payload)} sanitized record(s). "
                f"Observed total transacted volume of ${total_transacted:,.2f}"
                + (f" with combined balance of ${total_balance:,.2f}." if has_balance else ".")
                + (f" Average portfolio risk index is {avg_risk:.2f}." if avg_risk is not None else "")
            )

            return SimulatedAnalysisResult(
                can_answer=True,
                status_label="ANALYSIS SYNTHESIZED",
                summary=summary,
                metrics=metrics,
                data_minimization_notice=(
                    "PII, full account numbers, contact details, and confidential audit notes were excluded "
                    "by the PROVEX gateway and were never ingested into this analysis."
                ),
            )

        # 3. Compliance & Audit Review
        elif purpose == "audit_compliance":
            has_flags = "suspicious_flag" in permitted_set
            has_notes = "audit_notes" in permitted_set
            has_risk = "risk_score" in permitted_set

            flagged_count = sum(1 for r in sanitized_payload if r.get("suspicious_flag") is True) if has_flags else 0
            high_risk_count = sum(1 for r in sanitized_payload if float(r.get("risk_score", 0.0)) > 0.5) if has_risk else 0

            metrics = {
                "records_evaluated": len(sanitized_payload),
                "suspicious_flags_detected": flagged_count if has_flags else "Excluded",
                "high_risk_anomalies": high_risk_count if has_risk else "Excluded",
                "audit_notes_available": has_notes,
            }

            summary = (
                f"Compliance audit synthesized from {len(sanitized_payload)} record(s). "
                f"Identified {flagged_count} flagged suspicious transaction(s) requiring tier-2 supervisory oversight. "
                f"{high_risk_count} record(s) exceeded the 0.50 risk threshold."
            )

            return SimulatedAnalysisResult(
                can_answer=True,
                status_label="AUDIT SYNTHESIZED",
                summary=summary,
                metrics=metrics,
                data_minimization_notice=(
                    "SSNs and unmasked credit card PANs were blocked by policy. Audit analysis operates "
                    "strictly on anonymized identifiers and compliance tags."
                ),
            )

        # 4. Model Training / Feature Extraction
        elif purpose == "model_training":
            feature_keys = [k for k in permitted_fields if k in ("transaction_amount", "risk_score", "merchant_category")]
            metrics = {
                "training_samples": len(sanitized_payload),
                "approved_feature_dimensions": feature_keys,
            }
            summary = (
                f"Feature extraction completed for model training: {len(sanitized_payload)} sample vectors generated "
                f"using approved dimensions {feature_keys}. Zero direct identity markers are present in feature weights."
            )
            return SimulatedAnalysisResult(
                can_answer=True,
                status_label="FEATURES EXTRACTED",
                summary=summary,
                metrics=metrics,
                data_minimization_notice="Identity attributes, names, and contact details were stripped to prevent model memorization.",
            )

        # 5. Generic Fallback for other purposes
        metrics = {
            "records_processed": len(sanitized_payload),
            "approved_fields_count": len(permitted_fields),
        }
        return SimulatedAnalysisResult(
            can_answer=True,
            status_label="DATA SYNTHESIZED",
            summary=f"Processed {len(sanitized_payload)} record(s) based strictly on permitted fields {permitted_fields}.",
            metrics=metrics,
            data_minimization_notice="Unapproved attributes were pruned prior to processing.",
        )
