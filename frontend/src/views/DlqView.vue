<template>
  <article class="card">
    <h2>DLQ</h2>
    <p class="meta">Requeue or discard failed jobs with review metadata.</p>
    <button class="secondary" @click="reload">Refresh</button>
    <p class="error" v-if="error">{{ error }}</p>

    <table v-if="rows.length">
      <thead>
        <tr>
          <th>Item ID</th>
          <th>Job ID</th>
          <th>Error Code</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in rows" :key="item.item_id">
          <td>{{ item.item_id }}</td>
          <td>{{ item.job_id }}</td>
          <td>{{ item.error_code }}</td>
          <td>{{ item.status }}</td>
          <td>
            <button class="secondary" @click="runRequeue(item.item_id)">Requeue</button>
            <button class="danger" @click="runDiscard(item.item_id)">Discard</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="meta" v-else>No DLQ item found.</p>
  </article>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { discardDlqItem, listDlqItems, requeueDlqItem } from "../api";

const rows = ref([]);
const error = ref("");

async function reload() {
  error.value = "";
  try {
    const data = await listDlqItems();
    rows.value = data.items || [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function runRequeue(itemId) {
  error.value = "";
  try {
    await requeueDlqItem(itemId, "operator_requeue");
    await reload();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function runDiscard(itemId) {
  error.value = "";
  try {
    await discardDlqItem(itemId, {
      reason: "operator_discard",
      reviewer_id: "reviewer_frontend"
    });
    await reload();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

onMounted(reload);
</script>
