<template>
  <section class="grid two-col">
    <article class="card">
      <h2>Create Evaluation</h2>
      <div>
        <label>Project ID</label>
        <input v-model="form.projectId" :disabled="!canEvaluate" />
      </div>
      <div>
        <label>Supplier ID</label>
        <input v-model="form.supplierId" :disabled="!canEvaluate" />
      </div>
      <div>
        <label>Rule Pack Version</label>
        <input v-model="form.rulePackVersion" :disabled="!canEvaluate" />
      </div>
      <p class="meta" v-if="!canEvaluate">当前角色没有发起评估权限。</p>
      <button @click="submitEvaluation" :disabled="!canEvaluate">Submit</button>
      <p class="error" v-if="error">{{ error }}</p>
    </article>

    <article class="card">
      <h2>Evaluation Job</h2>
      <p class="meta" v-if="!lastJobId">No evaluation submitted yet.</p>
      <template v-else>
        <p><strong>Job ID:</strong> {{ lastJobId }}</p>
        <p v-if="lastEvaluationId"><strong>Evaluation ID:</strong> {{ lastEvaluationId }}</p>
        <p><strong>Status:</strong> {{ lastStatus || "unknown" }}</p>
        <button class="secondary" @click="refreshJob">Refresh Job</button>
        <RouterLink
          v-if="lastEvaluationId"
          class="secondary link-button"
          :to="`/evaluations/${lastEvaluationId}/report`"
        >
          Open Report
        </RouterLink>
      </template>
    </article>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { createEvaluation, getJob } from "../api";
import { useSessionStore } from "../stores/session";

const form = reactive({
  projectId: "prj_demo",
  supplierId: "sup_demo",
  rulePackVersion: "v1.0.0"
});

const lastJobId = ref("");
const lastStatus = ref("");
const lastEvaluationId = ref("");
const error = ref("");
const session = useSessionStore();
const canEvaluate = computed(() => session.can("evaluate"));

async function submitEvaluation() {
  error.value = "";
  if (!canEvaluate.value) {
    error.value = "permission_denied";
    return;
  }
  try {
    const created = await createEvaluation({
      project_id: form.projectId,
      supplier_id: form.supplierId,
      rule_pack_version: form.rulePackVersion,
      evaluation_scope: {
        include_doc_types: ["bid"],
        force_hitl: false
      },
      query_options: {
        mode_hint: "hybrid",
        top_k: 20
      }
    });
    lastJobId.value = created.job_id;
    lastEvaluationId.value = created.evaluation_id;
    await refreshJob();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function refreshJob() {
  if (!lastJobId.value) {
    return;
  }
  try {
    const job = await getJob(lastJobId.value);
    lastStatus.value = job.status || "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}
</script>
