import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:5173";
const apiBase = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8010";
const tenantId = process.env.E2E_TENANT_ID || "tenant_demo";

async function apiRequest(path, options = {}) {
  const headers = {
    "x-tenant-id": tenantId,
    "x-trace-id": `trace_${Math.random().toString(16).slice(2, 10)}`,
    ...(options.headers || {})
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    const message = payload?.error?.code || payload?.error?.message || response.statusText;
    throw new Error(message);
  }
  return payload.data;
}

async function uploadDocument() {
  const pdfBytes = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF");
  const form = new FormData();
  form.append("project_id", "prj_e2e");
  form.append("supplier_id", "sup_e2e");
  form.append("doc_type", "bid");
  form.append("file", new Blob([pdfBytes], { type: "application/pdf" }), "e2e.pdf");
  const resp = await fetch(`${apiBase}/api/v1/documents/upload`, {
    method: "POST",
    headers: {
      "Idempotency-Key": `idem_${Date.now()}`,
      "x-tenant-id": tenantId,
      "x-trace-id": `trace_${Math.random().toString(16).slice(2, 10)}`
    },
    body: form
  });
  const payload = await resp.json();
  if (!resp.ok || payload.success === false) {
    throw new Error(payload?.error?.code || payload?.error?.message || resp.statusText);
  }
  return payload.data;
}

async function run() {
  const upload = await uploadDocument();
  await apiRequest(`/api/v1/internal/jobs/${upload.job_id}/run`, {
    method: "POST",
    headers: { "x-internal-debug": "true" }
  });

  const evaluation = await apiRequest("/api/v1/evaluations", {
    method: "POST",
    headers: { "Idempotency-Key": `idem_${Date.now()}` },
    body: JSON.stringify({
      project_id: "prj_e2e",
      supplier_id: "sup_e2e",
      rule_pack_version: "v1.0.0",
      evaluation_scope: { include_doc_types: ["bid"], force_hitl: true },
      query_options: { mode_hint: "hybrid", top_k: 5 }
    })
  });
  const report = await apiRequest(`/api/v1/evaluations/${evaluation.evaluation_id}/report`);
  if (!report.evaluation_id) {
    throw new Error("report_missing");
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.goto(`${baseUrl}/evaluations/${report.evaluation_id}/report`, {
    waitUntil: "domcontentloaded"
  });
  await page.waitForSelector("h2");
  const reportHeader = await page.textContent(".report-header h2");
  if (!reportHeader || !reportHeader.includes("Evaluation Report")) {
    throw new Error("report_view_missing");
  }
  const criteria = page.locator(".criteria-table");
  const errorBox = page.locator(".error");
  await Promise.race([
    criteria.waitFor({ state: "visible", timeout: 30000 }),
    errorBox.waitFor({ state: "visible", timeout: 30000 })
  ]);
  if (await errorBox.isVisible()) {
    const message = await errorBox.textContent();
    throw new Error(`report_error:${message}`);
  }
  if (!(await criteria.isVisible())) {
    const content = await page.content();
    throw new Error(`report_missing_table:${content.slice(0, 400)}`);
  }
  await page.waitForSelector(".evidence-card");

  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
