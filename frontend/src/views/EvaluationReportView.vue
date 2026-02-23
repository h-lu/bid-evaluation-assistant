<template>
  <section class="report-layout">
    <article class="card">
      <div class="report-header">
        <div>
          <h2>Evaluation Report</h2>
          <p class="meta">Evaluation ID: {{ evaluationId }}</p>
        </div>
        <div class="report-actions">
          <button class="secondary" @click="loadReport">Refresh</button>
        </div>
      </div>
      <p class="error" v-if="error">{{ error }}</p>
      <div v-if="report">
        <div class="report-meta">
          <div><strong>Supplier:</strong> {{ report.supplier_id }}</div>
          <div><strong>Total Score:</strong> {{ report.total_score }}</div>
          <div><strong>Confidence:</strong> {{ report.confidence }}</div>
          <div><strong>Citation Coverage:</strong> {{ report.citation_coverage }}</div>
          <div v-if="report.score_deviation_pct !== undefined">
            <strong>Score Deviation:</strong> {{ report.score_deviation_pct }}%
          </div>
          <div v-if="report.report_uri">
            <strong>Report URI:</strong> {{ report.report_uri }}
          </div>
          <div><strong>Risk Level:</strong> {{ report.risk_level }}</div>
          <div v-if="report.redline_conflict"><strong>Redline Conflict:</strong> yes</div>
          <div v-if="report.unsupported_claims?.length">
            <strong>Unsupported Claims:</strong> {{ report.unsupported_claims.join(", ") }}
          </div>
        </div>
        <div class="criteria-table">
          <table>
            <thead>
              <tr>
                <th>Criteria</th>
                <th>Requirement</th>
                <th>Response</th>
                <th>Score</th>
                <th>Hard Pass</th>
                <th>Confidence</th>
                <th>Reason</th>
                <th>Citations</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in report.criteria_results" :key="item.criteria_id">
                <td>{{ item.criteria_name || item.criteria_id }}</td>
                <td>{{ item.requirement_text || "-" }}</td>
                <td>{{ item.response_text || "-" }}</td>
                <td>{{ item.score }} / {{ item.max_score }}</td>
                <td>{{ item.hard_pass ? "yes" : "no" }}</td>
                <td>{{ item.confidence ?? "-" }}</td>
                <td>{{ item.reason }}</td>
                <td>
                  <div class="meta">Count: {{ item.citations_count ?? item.citations?.length ?? 0 }}</div>
                  <button
                    v-for="cid in item.citations"
                    :key="cid"
                    class="chip"
                    @click="selectCitation(cid)"
                  >
                    {{ cid }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="meta">No report loaded.</div>
    </article>

    <article class="card evidence-card">
      <h3>Evidence</h3>
      <p class="meta">Click a citation to jump and highlight.</p>
      <div v-if="selectedCitation" class="evidence-meta">
        <div><strong>Document:</strong> {{ selectedCitation.document_id }}</div>
        <div><strong>Page:</strong> {{ selectedCitation.page }}</div>
        <div><strong>Chunk:</strong> {{ selectedCitation.chunk_id }}</div>
        <div v-if="selectedCitation.chunk_type">
          <strong>Chunk Type:</strong> {{ selectedCitation.chunk_type }}
        </div>
        <div v-if="selectedCitation.heading_path?.length">
          <strong>Heading:</strong> {{ selectedCitation.heading_path.join(" / ") }}
        </div>
      </div>
      <div v-if="selectedCitation?.text" class="quote">
        “{{ selectedCitation.text }}”
      </div>
      <div v-if="selectedCitation?.context" class="meta">
        {{ selectedCitation.context }}
      </div>
        <div class="pdf-pane">
          <div class="pdf-header">
            <span>PDF Preview</span>
            <span v-if="selectedCitation">Page {{ selectedCitation.page }}</span>
          </div>
        <div class="pdf-canvas">
          <canvas ref="pdfCanvas" class="pdf-page"></canvas>
          <div v-if="highlightStyle" class="highlight-box" :style="highlightStyle"></div>
        </div>
        <p class="meta" v-if="!selectedCitation">Select a citation to render highlight.</p>
      </div>
    </article>

    <article v-if="report?.interrupt" class="card review-card">
      <h3>Human Review Required</h3>
      <p class="meta">This evaluation is waiting for manual decision.</p>
      <ul class="meta" v-if="hitlReasons.length">
        <li v-for="reason in hitlReasons" :key="reason">{{ reason }}</li>
      </ul>
      <div class="review-form">
        <label>Decision</label>
        <select v-model="reviewForm.decision">
          <option value="approve">approve</option>
          <option value="reject">reject</option>
          <option value="edit_scores">edit_scores</option>
        </select>
        <label>Comment</label>
        <textarea v-model="reviewForm.comment" rows="3"></textarea>
        <p class="meta" v-if="!canReview">当前角色没有复核权限。</p>
        <button :disabled="!canReview" @click="submitReview">Submit Review</button>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import { getCitationSource, getDocumentRaw, getEvaluationReport, resumeEvaluation } from "../api";
import { useSessionStore } from "../stores/session";
import * as pdfjsLib from "pdfjs-dist/build/pdf";
import pdfWorker from "pdfjs-dist/build/pdf.worker?url";

const route = useRoute();
const evaluationId = computed(() => route.params.evaluation_id);
const report = ref(null);
const error = ref("");
const selectedCitation = ref(null);
const highlightStyle = ref(null);
const pdfCanvas = ref(null);
const pdfViewport = ref(null);
const pdfState = reactive({
  doc: null,
  documentId: null,
  page: 1,
  scale: 1.4
});
const session = useSessionStore();
const canReview = computed(() => session.can("review"));
const hitlReasons = computed(() => {
  if (!report.value) return [];
  const reasons = [];
  if (typeof report.value.confidence === "number" && report.value.confidence < 0.65) {
    reasons.push("low_confidence");
  }
  if (typeof report.value.citation_coverage === "number" && report.value.citation_coverage < 0.9) {
    reasons.push("low_citation_coverage");
  }
  if (
    typeof report.value.score_deviation_pct === "number" &&
    report.value.score_deviation_pct > 20
  ) {
    reasons.push("score_deviation_high");
  }
  if (report.value.redline_conflict) {
    reasons.push("redline_conflict");
  }
  if (Array.isArray(report.value.unsupported_claims) && report.value.unsupported_claims.length) {
    reasons.push("unsupported_claims");
  }
  return reasons;
});

const reviewForm = reactive({
  decision: "approve",
  comment: ""
});

async function loadReport() {
  error.value = "";
  try {
    report.value = await getEvaluationReport(evaluationId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function selectCitation(chunkId) {
  error.value = "";
  try {
    selectedCitation.value = await getCitationSource(chunkId);
    if (selectedCitation.value?.document_id) {
      await loadPdf(selectedCitation.value.document_id, selectedCitation.value.page || 1);
    }
    highlightStyle.value = mapHighlight(selectedCitation.value?.bbox || []);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function submitReview() {
  if (!report.value?.interrupt?.resume_token) {
    error.value = "missing_resume_token";
    return;
  }
  if (!canReview.value) {
    error.value = "permission_denied";
    return;
  }
  try {
    await resumeEvaluation(evaluationId.value, {
      resume_token: report.value.interrupt.resume_token,
      decision: reviewForm.decision,
      comment: reviewForm.comment,
      editor: { reviewer_id: "frontend_user" }
    });
    await loadReport();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

function mapHighlight(bbox) {
  if (!Array.isArray(bbox) || bbox.length !== 4 || !pdfViewport.value) {
    return null;
  }
  const [x0, y0, x1, y1] = bbox.map((v) => Number(v) || 0);
  const rect = pdfViewport.value.convertToViewportRectangle([x0, y0, x1, y1]);
  const left = Math.min(rect[0], rect[2]);
  const top = Math.min(rect[1], rect[3]);
  const width = Math.abs(rect[2] - rect[0]);
  const height = Math.abs(rect[3] - rect[1]);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  };
}

async function loadPdf(documentId, pageNumber) {
  if (!pdfCanvas.value) return;
  if (pdfState.documentId !== documentId) {
    const raw = await getDocumentRaw(documentId);
    const loadingTask = pdfjsLib.getDocument({ data: raw.buffer });
    pdfState.doc = await loadingTask.promise;
    pdfState.documentId = documentId;
  }
  if (!pdfState.doc) return;
  pdfState.page = pageNumber;
  const page = await pdfState.doc.getPage(pageNumber);
  const viewport = page.getViewport({ scale: pdfState.scale });
  pdfViewport.value = viewport;
  const canvas = pdfCanvas.value;
  const context = canvas.getContext("2d");
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  await page.render({ canvasContext: context, viewport }).promise;
}

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

onMounted(loadReport);
</script>
