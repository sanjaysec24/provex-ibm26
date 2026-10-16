import type {
  HealthResponse,
  GatewayQueryRequest,
  GatewayQueryResponse,
  ReceiptVerificationResponse,
  AuditReceipt,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function submitGatewayQuery(req: GatewayQueryRequest): Promise<GatewayQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/gateway/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gateway request failed (${response.status}): ${errorText}`);
  }
  return response.json();
}

export async function verifyAuditReceipt(receipt: AuditReceipt): Promise<ReceiptVerificationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/audit/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ receipt }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Verification failed (${response.status}): ${errorText}`);
  }
  return response.json();
}
