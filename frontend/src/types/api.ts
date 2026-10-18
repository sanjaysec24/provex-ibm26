export type UserRole =
  | 'compliance_auditor'
  | 'financial_analyst'
  | 'data_scientist'
  | 'guest'
  | 'anonymous';

export type DecisionAction = 'ALLOW' | 'REDACT' | 'DENY';

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
  target_resource: string;
  record_id?: string | null;
  actor_role: string;
  purpose: string;
  policy_id: string;
  action_decision: DecisionAction;
  permitted_fields: string[];
  redacted_fields: string[];
  blocked_fields: string[];
  payload_digest: string;
  receipt_digest: string;
}

export interface GatewayQueryRequest {
  query: string;
  actor_role: UserRole;
  purpose?: string;
  actor_id?: string;
  target_resource?: string;
  record_id?: string | null;
  requested_fields?: string[] | null;
}

export interface GatewayQueryResponse {
  request_id: string;
  timestamp: string;
  actor_role: string;
  purpose: string;
  target_resource: string;
  decision: DecisionAction;
  decision_reason: string;
  permitted_fields: string[];
  redacted_fields: string[];
  sanitized_payload?: Record<string, unknown>[] | null;
  audit_receipt: AuditReceipt;
  auth_disclaimer?: string;
}

export interface ReceiptVerificationRequest {
  receipt: AuditReceipt;
}

export interface ReceiptVerificationResponse {
  is_valid: boolean;
  receipt_id: string;
  verified_at: string;
  expected_digest: string;
  supplied_digest: string;
  details: string;
}

export interface DatasetUploadResponse {
  filename: string;
  target_resource: string;
  row_count: number;
  detected_columns: string[];
  record_ids: string[];
  preview_records: Record<string, unknown>[];
  message: string;
}
