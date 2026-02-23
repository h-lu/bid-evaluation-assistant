<template>
  <article class="card">
    <h2>DLQ</h2>
    <p class="meta">Requeue or discard failed jobs with review metadata.</p>
    <button class="secondary" @click="reload">Refresh</button>
    <p class="error" v-if="error">{{ error }}</p>
    <div class="dlq-approver">
      <div>
        <label>Reviewer A</label>
        <input v-model="reviewerA" :disabled="!canDiscard" />
      </div>
      <div>
        <label>Reviewer B</label>
        <input v-model="reviewerB" :disabled="!canDiscard" />
      </div>
    </div>

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
        <tr v-for="item in rows" :key="item.dlq_id">
          <td>{{ item.dlq_id }}</td>
          <td>{{ item.job_id }}</td>
          <td>{{ item.error_code }}</td>
          <td>{{ item.status }}</td>
          <td>
            <button class="secondary" @click="runRequeue(item.dlq_id)" :disabled="!canRequeue">
              Requeue
            </button>
            <button class="danger" @click="runDiscard(item.dlq_id)" :disabled="!canDiscard">
              Discard
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="meta" v-else>No DLQ item found.</p>
  </article>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";

import { discardDlqItem, listDlqItems, requeueDlqItem } from "../api";
import { useSessionStore } from "../stores/session";

const rows = ref([]);
const error = ref("");
const reviewerA = ref("reviewer_frontend_a");
const reviewerB = ref("reviewer_frontend_b");
const session = useSessionStore();
const canRequeue = computed(() => session.can("dlq_requeue"));
const canDiscard = computed(() => session.can("dlq_discard"));

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
  if (!canRequeue.value) {
    error.value = "permission_denied";
    return;
  }
  try {
    await requeueDlqItem(itemId, "operator_requeue");
    await reload();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function runDiscard(itemId) {
  error.value = "";
  if (!canDiscard.value) {
    error.value = "permission_denied";
    return;
  }
  if (!reviewerA.value || !reviewerB.value || reviewerA.value === reviewerB.value) {
    error.value = "reviewers_required";
    return;
  }
  if (!window.confirm("Discard requires dual approval. Continue?")) {
    return;
  }
  try {
    await discardDlqItem(itemId, {
      reason: "operator_discard",
      reviewer_id: reviewerA.value,
      reviewer_id_2: reviewerB.value
    });
    await reload();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
}

onMounted(reload);
</script>
