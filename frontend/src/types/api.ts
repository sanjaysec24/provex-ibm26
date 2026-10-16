export type UserRole =
  | 'compliance_auditor'
  | 'financial_analyst'
  | 'data_scientist'
  | 'guest'
  | 'anonymous';

export type DecisionAction = 'ALLOW' | 'REDACT_AND_ALLOW' | 'DENY';

export interface HealthResponse {
  status: string;
  timestamp: string;
  environment: string;
  data_adapter: string;
  policy_engine_active: boolean;
}

export interface AuditReceipt {
  receipt_id: string;
  timestamp: string;
  algorithm: string;
  actor_role: string;
  action_decision: DecisionAction;
  total_fields: number;
  redacted_fields_count: number;
  redacted_field_names: string[];
  payload_digest: string;
  receipt_digest: string;
}

export interface GatewayQueryRequest {
  query: string;
  actor_role: UserRole;
  actor_id?: string;
  target_resource?: string;
}

export interface GatewayQueryResponse {
  request_id: string;
  timestamp: string;
  actor_role: string;
  decision: DecisionAction;
  decision_reason: string;
  redacted_fields: string[];
  sanitized_payload?: Record<string, unknown>[] | null;
  audit_receipt: AuditReceipt;
}

export interface ReceiptVerificationRequest {
  receipt: AuditReceipt;
}

export interface ReceiptVerificationResponse {
  is_valid: boolean;
  receipt_id: string;
  verified_at: string;
  details: string;
}
