# PROVEX — AI Security Gateway

> **Give AI exactly what it needs — and nothing more.**

PROVEX is a prototype security gateway designed to reduce unnecessary exposure of sensitive enterprise data to downstream AI systems. It applies deterministic backend policies, filters records to approved fields, demonstrates a simulated AI consumer, and produces SHA-256 audit receipts that can be checked for modification.

## Why PROVEX?

Enterprise AI workflows may expose more data than a task requires. PROVEX demonstrates a controlled path in which policy is evaluated before data is released, data is minimized on the server, and the resulting decision can be inspected.

## Features

- **Deterministic, fail-closed policy engine** for role, purpose, resource, and field-level decisions.
- **Server-side data sanitization** so only permitted fields are passed downstream.
- **CSV dataset ingestion** through `POST /api/v1/dataset/upload`, with validation and an in-memory mock adapter.
- **Interactive React dashboard** for requests, policy traces, sanitized payloads, and session activity.
- **Deterministic simulated AI consumer** that operates on sanitized data; no external LLM API is called.
- **SHA-256 audit receipts** with an endpoint to check whether receipt contents match the recorded digest.
- **Tamper demonstration** that checks a modified copy of a receipt.
- **Synthetic demo data** for local evaluation without a live enterprise data connection.

## Architecture

```text
Browser (React + TypeScript)
          |
          | HTTP / JSON + multipart CSV upload
          v
FastAPI API
  ├── Health: GET  /api/v1/health
  ├── CSV upload: POST /api/v1/dataset/upload
  ├── Gateway: POST /api/v1/gateway/process
  └── Receipt verification: POST /api/v1/audit/verify
          |
          v
Deterministic Policy Engine
          |
          v
Server-side Data Sanitizer
          |
          v
Sanitized payload only
          |
          v
Deterministic Simulated Consumer

Audit receipt -> SHA-256 digest verification
Data source  -> In-memory synthetic/mock adapter
```

**Security invariant:** the deterministic backend policy engine is the authorization authority. Natural-language prompt text does not grant permission. Denied requests must not release a sanitized payload to the consumer.

## Technology stack

- **Frontend:** React, TypeScript, Vite, Lucide
- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Validation / tests:** pytest, HTTPX
- **Upload handling:** `python-multipart`
- **Audit integrity demo:** canonical JSON serialization and SHA-256

Check the project dependency files for the exact versions used in your checkout.

## Requirements

- Windows PowerShell (commands below use Windows paths)
- Python and the project virtual environment
- Node.js and npm

## Run locally

Open two terminals from the project root.

### 1. Start the backend

```powershell
cd C:\Users\admin\ibm-2026
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Keep this terminal open.

Useful backend URLs:

- Health: <http://127.0.0.1:8000/api/v1/health>
- Interactive API docs: <http://127.0.0.1:8000/docs>

### 2. Start the frontend

In a second terminal:

```powershell
cd C:\Users\admin\ibm-2026\frontend
npm run dev
```

Open the local URL printed by Vite, normally <http://localhost:5173>.

### 3. Demo workflow

1. Use **Load Demo Sample CSV** or select a supported CSV file in the dataset ingestion panel.
2. Confirm that the upload result shows the number of ingested rows and detected columns.
3. Select an uploaded record identifier to populate the gateway request.
4. Submit a request using a supported demo role, resource, and purpose.
5. Inspect the policy decision and the sanitized payload.
6. Confirm that denied requests do not provide a payload to the simulated consumer.
7. Verify the audit receipt.
8. Use the tamper sandbox to modify a copy of the receipt and verify that the modified copy is rejected.

### CSV upload contract

The reported prototype endpoint is:

`POST /api/v1/dataset/upload`

It accepts `multipart/form-data` with:

- `file`: CSV file
- `target_resource`: supported resource type (`accounts` or `transactions` in the current upload implementation)

The current implementation report specifies a 1 MB file limit and a maximum of 100 rows. The server validates encoding, required identifier columns, and headers against known resource schemas. Consult `/docs` for the exact live request/response schema.

Uploaded datasets are held in memory and are lost when the backend process restarts. Use synthetic, non-sensitive demo records only.

## Tests and build checks

Run the backend tests from the project root:

```powershell
cd C:\Users\admin\ibm-2026
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

Run frontend lint and production build:

```powershell
cd C:\Users\admin\ibm-2026\frontend
npm run lint
npm run build
```

The implementation report for checkpoint `04f9c54` reported **41 backend tests passing**, frontend lint clean, and a successful production build. Re-run the commands above to verify the current checkout.

## Security and prototype limitations

- **Not production authentication:** the role selector is a demo clearance assumption, not trusted JWT/OIDC identity.
- **Synthetic data only:** the mock adapter is used for the current demonstration.
- **No live IBM integration:** the LinuxONE/Db2 adapter remains a placeholder; this repository should not be described as connected to a live IBM Z or LinuxONE system.
- **No live LLM:** downstream analysis is deterministic and simulated.
- **In-memory uploads:** uploaded data is lost when the backend restarts.
- **SHA-256 caveat:** a plain digest can detect changes relative to a supplied digest, but does not by itself prove who created a receipt or prevent an attacker from replacing both the receipt and digest. It is not a digital signature.
- **Prototype scope:** do not use real customer data, credentials, or production workloads.

## IBM Z / LinuxONE relevance

PROVEX is designed for a potential integration in which a replaceable data adapter retrieves approved fields from Db2 in an IBM Z/LinuxONE environment while the same policy and sanitization boundary remains in place. **This integration is planned, not implemented or live in the current prototype.**

## Project status

The reported Git checkpoint is `04f9c54` (`feat: implement CSV dataset upload endpoint, zero-trust schema validation, and interactive demo flow`). Features and results in this README should be re-verified against the repository before final submission.

## License

No license is specified here. Add a license file only after choosing the license you intend to apply to this project.
