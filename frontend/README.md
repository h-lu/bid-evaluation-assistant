# Frontend (Vue3 + Vite)

## Local Run

```bash
cd frontend
npm install
npm run dev
```

Default API base URL: `http://localhost:8000`  
Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Implemented Scope

1. Route skeleton aligned with `docs/design/2026-02-21-frontend-interaction-spec.md`.
2. Core pages:
   - `/dashboard`
   - `/documents`
   - `/evaluations`
   - `/jobs`
   - `/dlq`
3. API integration for health, document upload, evaluation create, jobs list/detail, DLQ requeue/discard.

## Next Iteration

1. SSE/polling hybrid job state sync.
2. Evaluation report + citation jump and bbox highlight.
3. Role-based route guards and audit page implementation.
