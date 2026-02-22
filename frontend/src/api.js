const defaultTenant = "tenant_demo";
const defaultTrace = () => `trace_${Math.random().toString(16).slice(2, 12)}`;
const defaultIdempotencyKey = () => `idem_${Math.random().toString(16).slice(2, 14)}`;
const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiRequest(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "x-tenant-id": defaultTenant,
    "x-trace-id": defaultTrace(),
    ...(options.headers || {})
  };
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload?.error?.code || payload?.error?.message || response.statusText);
  }
  return payload.data;
}

export function getHealth() {
  return apiRequest("/healthz", { method: "GET" });
}

export function createEvaluation(body) {
  return apiRequest("/api/v1/evaluations", {
    method: "POST",
    body: JSON.stringify(body),
    headers: {
      "Idempotency-Key": defaultIdempotencyKey()
    }
  });
}

export function getJob(jobId) {
  return apiRequest(`/api/v1/jobs/${jobId}`, { method: "GET" });
}

export function listJobs() {
  return apiRequest("/api/v1/jobs?limit=50", { method: "GET" });
}

export function uploadDocument(file, projectId, supplierId, docType) {
  const form = new FormData();
  form.append("file", file);
  form.append("project_id", projectId);
  form.append("supplier_id", supplierId);
  form.append("doc_type", docType);
  return fetch(`${baseUrl}/api/v1/documents/upload`, {
    method: "POST",
    headers: {
      "x-tenant-id": defaultTenant,
      "x-trace-id": defaultTrace(),
      "Idempotency-Key": defaultIdempotencyKey()
    },
    body: form
  })
    .then((resp) => resp.json())
    .then((payload) => {
      if (payload.success === false) {
        throw new Error(payload?.error?.code || "upload_failed");
      }
      return payload.data;
    });
}

export function listDlqItems() {
  return apiRequest("/api/v1/dlq/items", { method: "GET" });
}

export function requeueDlqItem(itemId, reason) {
  return apiRequest(`/api/v1/dlq/items/${itemId}/requeue`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export function discardDlqItem(itemId, payload) {
  return apiRequest(`/api/v1/dlq/items/${itemId}/discard`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
