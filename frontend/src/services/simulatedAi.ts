import type { DecisionAction } from '../types/api';

export interface SimulatedAnalysisResult {
  canAnswer: boolean;
  statusLabel: string;
  summary: string;
  metrics: Record<string, string | number | boolean | string[]>;
  dataMinimizationNotice: string;
  disclaimer: string;
}

/**
 * Deterministic simulated AI consumer for the PROVEX dashboard.
 * Consumes strictly the sanitized payload returned by the gateway.
 */
export function runSimulatedAiAnalysis(
  decision: DecisionAction,
  permittedFields: string[],
  sanitizedPayload?: Record<string, unknown>[] | null,
  purpose: string = 'portfolio_analysis',
  targetResource: string = 'financial_records'
): SimulatedAnalysisResult {
  const disclaimer = 'DETERMINISTIC SIMULATION: Evaluates approved fields only. No external LLM or AI API invoked.';

  // 1. Immediate halt on DENY or missing data
  if (decision === 'DENY' || !sanitizedPayload || sanitizedPayload.length === 0) {
    return {
      canAnswer: false,
      statusLabel: 'BLOCKED: Access Denied',
      summary: `Simulated AI ingestion halted. The deterministic security gateway denied access to resource '${targetResource}'. Zero source records reached downstream processing.`,
      metrics: {},
      dataMinimizationNotice: 'Zero fields transmitted to simulated consumer.',
      disclaimer,
    };
  }

  const permittedSet = new Set(permittedFields);

  // 2. Portfolio Analysis
  if (purpose === 'portfolio_analysis') {
    const hasBalance = permittedSet.has('account_balance');
    const hasAmount = permittedSet.has('transaction_amount');
    const hasRisk = permittedSet.has('risk_score');

    if (!hasBalance && !hasAmount) {
      return {
        canAnswer: false,
        statusLabel: 'INSUFFICIENT DATA',
        summary: 'Cannot generate portfolio analysis: Financial figures (balance/amount) were not approved by policy.',
        metrics: {},
        dataMinimizationNotice: 'Account balances and transaction amounts were pruned by data minimization.',
        disclaimer,
      };
    }

    let totalBalance = 0;
    let totalAmount = 0;
    let riskSum = 0;
    let riskCount = 0;

    for (const record of sanitizedPayload) {
      if (typeof record.account_balance === 'number') totalBalance += record.account_balance;
      if (typeof record.transaction_amount === 'number') totalAmount += record.transaction_amount;
      if (hasRisk && typeof record.risk_score === 'number') {
        riskSum += record.risk_score;
        riskCount += 1;
      }
    }

    const avgRisk = riskCount > 0 ? (riskSum / riskCount).toFixed(2) : 'Excluded';

    return {
      canAnswer: true,
      statusLabel: 'ANALYSIS SYNTHESIZED',
      summary: `Portfolio analysis synthesized across ${sanitizedPayload.length} record(s). Observed total transacted volume of $${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` +
        (hasBalance ? ` with combined balance of $${totalBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}.` : '.') +
        (riskCount > 0 ? ` Average portfolio risk index is ${avgRisk}.` : ''),
      metrics: {
        'Records Evaluated': sanitizedPayload.length,
        'Aggregate Balance': hasBalance ? `$${totalBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'Excluded',
        'Transaction Volume': hasAmount ? `$${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'Excluded',
        'Average Risk Score': avgRisk,
      },
      dataMinimizationNotice: 'PII, full account numbers, contact details, and confidential audit notes were excluded by PROVEX data minimization and were never ingested into this analysis.',
      disclaimer,
    };
  }

  // 3. Audit Compliance
  if (purpose === 'audit_compliance') {
    const hasFlags = permittedSet.has('suspicious_flag');
    const hasNotes = permittedSet.has('audit_notes');
    const hasRisk = permittedSet.has('risk_score');

    let flagCount = 0;
    let highRiskCount = 0;

    for (const record of sanitizedPayload) {
      if (record.suspicious_flag === true) flagCount += 1;
      if (typeof record.risk_score === 'number' && record.risk_score > 0.5) highRiskCount += 1;
    }

    return {
      canAnswer: true,
      statusLabel: 'AUDIT SYNTHESIZED',
      summary: `Compliance audit synthesized from ${sanitizedPayload.length} record(s). Identified ${flagCount} flagged suspicious transaction(s) requiring tier-2 supervisory oversight. ${highRiskCount} record(s) exceeded the 0.50 risk threshold.`,
      metrics: {
        'Records Evaluated': sanitizedPayload.length,
        'Suspicious Flags Detected': hasFlags ? flagCount : 'Excluded',
        'High-Risk Anomalies (>0.50)': hasRisk ? highRiskCount : 'Excluded',
        'Audit Notes Included': hasNotes ? 'Yes (Sanitized)' : 'No',
      },
      dataMinimizationNotice: 'SSNs and unmasked credit card PANs were blocked by policy. Audit analysis operates strictly on anonymized identifiers and compliance tags.',
      disclaimer,
    };
  }

  // 4. Model Training / Feature Extraction
  if (purpose === 'model_training') {
    const featureKeys = permittedFields.filter((f) =>
      ['transaction_amount', 'transaction_date', 'risk_score', 'merchant_category', 'fraud_label'].includes(f)
    );

    return {
      canAnswer: true,
      statusLabel: 'FEATURES EXTRACTED',
      summary: `Feature extraction completed for model training: ${sanitizedPayload.length} sample vectors generated using approved dimensions [${featureKeys.join(', ')}]. Zero direct identity markers are present in feature weights.`,
      metrics: {
        'Training Samples': sanitizedPayload.length,
        'Approved Dimensions': featureKeys.join(', '),
      },
      dataMinimizationNotice: 'Identity attributes, names, and contact details were stripped to prevent model memorization and PII exposure.',
      disclaimer,
    };
  }

  // 5. Generic Fallback
  return {
    canAnswer: true,
    statusLabel: 'DATA SYNTHESIZED',
    summary: `Processed ${sanitizedPayload.length} record(s) based strictly on permitted fields [${permittedFields.join(', ')}].`,
    metrics: {
      'Records Processed': sanitizedPayload.length,
      'Approved Fields Count': permittedFields.length,
    },
    dataMinimizationNotice: 'Unapproved attributes were pruned prior to processing.',
    disclaimer,
  };
}
