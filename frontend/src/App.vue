<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <h1>Bid Evaluation Assistant</h1>
        <p>Upload, evaluate, review, and archive with traceable evidence.</p>
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
</script>
