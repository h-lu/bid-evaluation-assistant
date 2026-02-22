<template>
  <article class="card">
    <h2>Jobs</h2>
    <p class="meta">Track async jobs by status and id.</p>
    <button class="secondary" @click="reload">Refresh</button>
    <p class="error" v-if="error">{{ error }}</p>
    <table v-if="rows.length">
      <thead>
        <tr>
          <th>Job ID</th>
          <th>Type</th>
          <th>Status</th>
          <th>Tenant</th>
          <th>Trace</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in rows" :key="job.job_id">
          <td>{{ job.job_id }}</td>
          <td>{{ job.job_type }}</td>
          <td>{{ job.status }}</td>
          <td>{{ job.tenant_id }}</td>
          <td>{{ job.trace_id }}</td>
        </tr>
      </tbody>
    </table>
    <p class="meta" v-else>No jobs returned.</p>
  </article>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { listJobs } from "../api";

const rows = ref([]);
const error = ref("");

async function reload() {
  error.value = "";
  try {
    const data = await listJobs();
    rows.value = data.items || [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

onMounted(reload);
</script>
