import type {
  HealthResponse,
  GatewayQueryRequest,
  GatewayQueryResponse,
  ReceiptVerificationResponse,
  AuditReceipt,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 8000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (err: unknown) {
    clearTimeout(id);
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs}ms. Backend might be overloaded or unreachable.`);
    }
    throw new Error(`Failed to connect to gateway at ${API_BASE_URL}. Ensure the backend is running.`);
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function submitGatewayQuery(req: GatewayQueryRequest): Promise<GatewayQueryResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/gateway/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(`Gateway request failed (${response.status}): ${errorDetail}`);
  }
  return response.json();
}

export async function verifyAuditReceipt(receipt: AuditReceipt): Promise<ReceiptVerificationResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/audit/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ receipt }),
  });
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(`Verification failed (${response.status}): ${errorDetail}`);
  }
  return response.json();
}
