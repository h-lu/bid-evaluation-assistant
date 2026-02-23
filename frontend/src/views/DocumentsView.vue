<template>
  <section class="grid two-col">
    <article class="card">
      <h2>Upload Document</h2>
      <div>
        <label>Project ID</label>
        <input v-model="form.projectId" :disabled="!canUpload" />
      </div>
      <div>
        <label>Supplier ID</label>
        <input v-model="form.supplierId" :disabled="!canUpload" />
      </div>
      <div>
        <label>Doc Type</label>
        <input v-model="form.docType" :disabled="!canUpload" />
      </div>
      <div>
        <label>File</label>
        <input type="file" @change="onFileChange" :disabled="!canUpload" />
      </div>
      <p class="error" v-if="error">{{ error }}</p>
      <p class="meta" v-if="!canUpload">当前角色没有上传权限。</p>
      <button @click="onUpload" :disabled="!canUpload">Upload</button>
    </article>

    <article class="card">
      <h2>Last Upload</h2>
      <p class="meta" v-if="!result">No upload yet.</p>
      <template v-else>
        <p><strong>Job ID:</strong> {{ result.job_id }}</p>
        <p><strong>Document ID:</strong> {{ result.document_id }}</p>
        <button class="secondary" @click="refreshJob" :disabled="!result.job_id">Refresh Job</button>
        <p class="meta" v-if="jobStatus">Current job status: {{ jobStatus }}</p>
      </template>
    </article>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from "vue";

import { getJob, uploadDocument } from "../api";
import { useSessionStore } from "../stores/session";

const form = reactive({
  projectId: "prj_demo",
  supplierId: "sup_demo",
  docType: "bid"
});
const selectedFile = ref(null);
const result = ref(null);
const error = ref("");
const jobStatus = ref("");
const session = useSessionStore();
const canUpload = computed(() => session.can("upload"));

function onFileChange(event) {
  const files = event.target.files;
  selectedFile.value = files && files.length ? files[0] : null;
}

async function onUpload() {
  error.value = "";
  jobStatus.value = "";
  if (!canUpload.value) {
    error.value = "permission_denied";
    return;
  }
  if (!selectedFile.value) {
    error.value = "Please select a file.";
    return;
  }
  try {
    result.value = await uploadDocument(selectedFile.value, form.projectId, form.supplierId, form.docType);
    if (result.value?.job_id) {
      await refreshJob();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function refreshJob() {
  if (!result.value?.job_id) {
    return;
  }
  try {
    const job = await getJob(result.value.job_id);
    jobStatus.value = job.status;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}
</script>
