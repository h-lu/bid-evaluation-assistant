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
          <div><strong>Risk Level:</strong> {{ report.risk_level }}</div>
        </div>
        <div class="criteria-table">
          <table>
            <thead>
              <tr>
                <th>Criteria</th>
                <th>Score</th>
                <th>Hard Pass</th>
                <th>Reason</th>
                <th>Citations</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in report.criteria_results" :key="item.criteria_id">
                <td>{{ item.criteria_id }}</td>
                <td>{{ item.score }} / {{ item.max_score }}</td>
                <td>{{ item.hard_pass ? "yes" : "no" }}</td>
                <td>{{ item.reason }}</td>
                <td>
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
      </div>
      <div v-if="selectedCitation?.quote" class="quote">
        “{{ selectedCitation.quote }}”
      </div>
      <div class="pdf-pane">
        <div class="pdf-header">
          <span>PDF Preview (mock)</span>
          <span v-if="selectedCitation">Page {{ selectedCitation.page }}</span>
        </div>
        <div class="pdf-canvas">
          <div class="pdf-page"></div>
          <div v-if="highlightStyle" class="highlight-box" :style="highlightStyle"></div>
        </div>
        <p class="meta" v-if="!selectedCitation">Select a citation to render highlight.</p>
      </div>
    </article>

    <article v-if="report?.interrupt" class="card review-card">
      <h3>Human Review Required</h3>
      <p class="meta">This evaluation is waiting for manual decision.</p>
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

import { getCitationSource, getEvaluationReport, resumeEvaluation } from "../api";
import { useSessionStore } from "../stores/session";

const route = useRoute();
const evaluationId = computed(() => route.params.evaluation_id);
const report = ref(null);
const error = ref("");
const selectedCitation = ref(null);
const highlightStyle = ref(null);
const session = useSessionStore();
const canReview = computed(() => session.can("review"));

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
  if (!Array.isArray(bbox) || bbox.length !== 4) {
    return null;
  }
  const [x0, y0, x1, y1] = bbox.map((v) => Number(v) || 0);
  const maxCoord = Math.max(x1, y1, 1);
  const norm = maxCoord > 1 ? 1 / maxCoord : 1;
  const left = Math.max(0, x0 * norm * 100);
  const top = Math.max(0, y0 * norm * 100);
  const width = Math.max(0, (x1 - x0) * norm * 100);
  const height = Math.max(0, (y1 - y0) * norm * 100);
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${width}%`,
    height: `${height}%`
  };
}

onMounted(loadReport);
</script>
