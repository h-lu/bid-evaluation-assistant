<template>
  <section class="grid two-col">
    <article class="card">
      <h2>Create Evaluation</h2>
      <div>
        <label>Project ID</label>
        <input v-model="form.projectId" />
      </div>
      <div>
        <label>Supplier ID</label>
        <input v-model="form.supplierId" />
      </div>
      <div>
        <label>Rule Pack Version</label>
        <input v-model="form.rulePackVersion" />
      </div>
      <button @click="submitEvaluation">Submit</button>
      <p class="error" v-if="error">{{ error }}</p>
    </article>

    <article class="card">
      <h2>Evaluation Job</h2>
      <p class="meta" v-if="!lastJobId">No evaluation submitted yet.</p>
      <template v-else>
        <p><strong>Job ID:</strong> {{ lastJobId }}</p>
        <p><strong>Status:</strong> {{ lastStatus || "unknown" }}</p>
        <button class="secondary" @click="refreshJob">Refresh Job</button>
      </template>
    </article>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";

import { createEvaluation, getJob } from "../api";

const form = reactive({
  projectId: "prj_demo",
  supplierId: "sup_demo",
  rulePackVersion: "v1.0.0"
});

const lastJobId = ref("");
const lastStatus = ref("");
const error = ref("");

async function submitEvaluation() {
  error.value = "";
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
