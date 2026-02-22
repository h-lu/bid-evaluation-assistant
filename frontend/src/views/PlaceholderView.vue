<template>
  <article class="card">
    <h2>{{ heading }}</h2>
    <p class="meta">This route is scaffolded and reserved for the next iteration.</p>
    <p class="meta">Route params: {{ serializedParams }}</p>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
  title: {
    type: String,
    default: ""
  }
});

const route = useRoute();
const heading = computed(() => props.title || route.path);
const serializedParams = computed(() => JSON.stringify(route.params));
</script>
