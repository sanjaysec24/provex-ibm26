import { useEffect, useState } from 'react';
import { ShieldCheck, Database, CheckCircle2, AlertTriangle, RefreshCw, Lock } from 'lucide-react';
import { fetchHealth } from './services/api';
import type { HealthResponse } from './types/api';

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async (isManual = false) => {
    if (isManual) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to connect to gateway');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    fetchHealth()
      .then((data) => {
        if (!ignore) {
          setHealth(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : 'Unable to connect to gateway');
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-slate-800 antialiased flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-[#EAE5DC] bg-white/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-200 flex items-center justify-center text-sky-600">
              <ShieldCheck className="w-6 h-6 text-sky-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold tracking-tight text-lg text-slate-900">PROVEX</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200">
                  IBM Z Datathon 2026
                </span>
              </div>
              <p className="text-xs text-slate-500">Deterministic AI Security Gateway & Audit System</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => checkHealth(true)}
              disabled={loading}
              className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-lg border border-[#EAE5DC] bg-[#FAF8F5] hover:bg-[#F3EFE6] text-slate-700 transition"
              title="Refresh Health Status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-600' : 'text-slate-500'}`} />
              <span>Refresh Status</span>
            </button>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Stage 1 Active</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        {/* Hero Section */}
        <div className="bg-white rounded-2xl border border-[#EAE5DC] p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-sky-50 text-sky-700 border border-sky-100 text-xs font-medium">
                <Lock className="w-3.5 h-3.5" />
                Zero-Trust Deterministic Security Boundary
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                Safe Enterprise Data Ingestion for AI Workloads
              </h1>
              <p className="text-sm text-slate-600 leading-relaxed">
                PROVEX intercepts queries before they reach AI models. Access decisions are strictly deterministic:
                unauthorized fields are redacted at the backend layer, default-deny is rigorously enforced, and every event
                produces a tamper-evident audit receipt.
              </p>
            </div>

            {/* Live Health Badge Card */}
            <div className="bg-[#FAF8F5] border border-[#EAE5DC] rounded-xl p-4 sm:w-80 flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Gateway Status</span>
                {loading ? (
                  <span className="text-xs font-medium text-slate-400">Verifying...</span>
                ) : health ? (
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded-full">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    Operational
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                    Offline / Connecting
                  </span>
                )}
              </div>

              <div className="space-y-1.5 text-xs text-slate-600">
                <div className="flex justify-between py-1 border-b border-[#EAE5DC]">
                  <span className="text-slate-500">Adapter:</span>
                  <span className="font-mono font-medium text-slate-800">{health?.data_adapter || 'synthetic (offline)'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#EAE5DC]">
                  <span className="text-slate-500">Policy Engine:</span>
                  <span className="font-medium text-emerald-700 font-mono">
                    {health?.policy_engine_active ? 'Active (Strict Deny)' : 'Standby'}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Environment:</span>
                  <span className="font-mono text-slate-800">{health?.environment || 'development'}</span>
                </div>
              </div>

              {error && (
                <div className="p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800">
                  Backend offline: run <code className="bg-amber-100 px-1 rounded">uvicorn app.main:app</code>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Security Pipeline Flow */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">PROVEX Security Pipeline</h2>
            <span className="text-xs text-slate-500">Architecture Contract (Stage 1)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Step 1 */}
            <div className="bg-white rounded-xl border border-[#EAE5DC] p-4 flex flex-col justify-between hover:border-sky-300 transition shadow-xs">
              <div className="space-y-2">
                <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center font-bold text-sm">
                  1
                </div>
                <h3 className="font-semibold text-slate-900 text-sm">Clearance Interceptor</h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Extracts actor identity and clearance role. If authentication or scope cannot be verified, immediately fails closed (Default Deny).
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#EAE5DC] text-[11px] font-mono text-slate-500">
                Rule: Default-Deny
              </div>
            </div>

            {/* Step 2 */}
            <div className="bg-white rounded-xl border border-[#EAE5DC] p-4 flex flex-col justify-between hover:border-sky-300 transition shadow-xs">
              <div className="space-y-2">
                <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center font-bold text-sm">
                  2
                </div>
                <h3 className="font-semibold text-slate-900 text-sm">Deterministic Policy Engine</h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Evaluates RBAC/ABAC clearance rules against requested resource attributes. Never delegates security decisions to an LLM.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#EAE5DC] text-[11px] font-mono text-slate-500">
                Zero AI hallucinations
              </div>
            </div>

            {/* Step 3 */}
            <div className="bg-white rounded-xl border border-[#EAE5DC] p-4 flex flex-col justify-between hover:border-sky-300 transition shadow-xs">
              <div className="space-y-2">
                <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center font-bold text-sm">
                  3
                </div>
                <h3 className="font-semibold text-slate-900 text-sm">Pre-AI Data Redaction</h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Strips PII, balances, and confidential fields at backend layer before synthetic or real records are packaged for AI prompt ingestion.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#EAE5DC] text-[11px] font-mono text-slate-500">
                PII never reaches model
              </div>
            </div>

            {/* Step 4 */}
            <div className="bg-white rounded-xl border border-[#EAE5DC] p-4 flex flex-col justify-between hover:border-sky-300 transition shadow-xs">
              <div className="space-y-2">
                <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center font-bold text-sm">
                  4
                </div>
                <h3 className="font-semibold text-slate-900 text-sm">SHA-256 Audit Receipt</h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Generates an immutable cryptographic digest linking the actor, policy decision, redacted field count, and sanitized payload hash.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#EAE5DC] text-[11px] font-mono text-slate-500">
                Tamper-evident proof
              </div>
            </div>
          </div>
        </section>

        {/* Architecture Isolation Notice */}
        <div className="bg-white rounded-xl border border-[#EAE5DC] p-5 flex items-start gap-4">
          <Database className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-slate-900">
              Data Adapter Isolation: 100% Synthetic & Offline Operation
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              PROVEX runs entirely on synthetic test fixtures by default with no live credentials or external IBM infrastructure dependencies.
              The IBM LinuxONE / Db2 adapter is designed as a drop-in replacement adhering to the identical <code className="bg-[#FAF8F5] px-1 py-0.5 rounded border border-[#EAE5DC] font-mono text-[11px]">DataSourceAdapter</code> interface.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#EAE5DC] bg-white py-4 text-center text-xs text-slate-500">
        <p>PROVEX — Deterministic AI Security Gateway • IBM Z Datathon 2026 • Stage 1 Scaffold Verified</p>
      </footer>
    </div>
  );
}

export default App;
