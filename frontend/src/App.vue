<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <h1>Bid Evaluation Assistant</h1>
        <p>Upload, evaluate, review, and archive with traceable evidence.</p>
      </div>
      <div class="session-panel">
        <div class="session-field">
          <label>Role</label>
          <select v-model="session.role">
            <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
          </select>
        </div>
        <div class="session-field">
          <label>Tenant</label>
          <input v-model="session.tenantId" />
        </div>
      </div>
      <nav class="menu">
        <RouterLink to="/dashboard">Dashboard</RouterLink>
        <RouterLink to="/documents">Documents</RouterLink>
        <RouterLink to="/evaluations">Evaluations</RouterLink>
        <RouterLink to="/jobs">Jobs</RouterLink>
        <RouterLink to="/dlq">DLQ</RouterLink>
      </nav>
    </header>
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from "vue-router";
import { useSessionStore } from "./stores/session";

const session = useSessionStore();
const roles = ["admin", "agent", "evaluator", "viewer"];
</script>
