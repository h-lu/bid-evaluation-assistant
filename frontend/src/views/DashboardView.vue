<template>
  <section class="grid two-col">
    <article class="card">
      <h2>System Health</h2>
      <p class="meta">Backend status from <code>/healthz</code>.</p>
      <p><strong>Status:</strong> {{ status }}</p>
      <p class="error" v-if="error">{{ error }}</p>
      <button class="secondary" @click="loadHealth">Refresh</button>
    </article>

    <article class="card">
      <h2>Operator Checklist</h2>
      <ol class="meta">
        <li>Upload documents and monitor parse jobs.</li>
        <li>Create evaluations and follow job lifecycle.</li>
        <li>Handle DLQ items with dual review when required.</li>
      </ol>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { getHealth } from "../api";

const status = ref("unknown");
const error = ref("");

async function loadHealth() {
  error.value = "";
  try {
    const data = await getHealth();
    status.value = data.status || "ok";
  } catch (err) {
    status.value = "unavailable";
    error.value = err instanceof Error ? err.message : String(err);
  }
}

onMounted(loadHealth);
</script>
