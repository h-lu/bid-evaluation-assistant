import { createRouter, createWebHistory } from "vue-router";

import DashboardView from "./views/DashboardView.vue";
import DlqView from "./views/DlqView.vue";
import DocumentsView from "./views/DocumentsView.vue";
import EvaluationsView from "./views/EvaluationsView.vue";
import JobsView from "./views/JobsView.vue";
import PlaceholderView from "./views/PlaceholderView.vue";

export const routes = [
  { path: "/login", component: PlaceholderView, props: { title: "Login" } },
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", component: DashboardView },
  { path: "/projects", component: PlaceholderView, props: { title: "Projects" } },
  { path: "/projects/:project_id", component: PlaceholderView, props: true },
  { path: "/projects/:project_id/rules", component: PlaceholderView, props: true },
  { path: "/documents", component: DocumentsView },
  { path: "/documents/:document_id", component: PlaceholderView, props: true },
  { path: "/evaluations", component: EvaluationsView },
  { path: "/evaluations/:evaluation_id", component: PlaceholderView, props: true },
  { path: "/evaluations/:evaluation_id/report", component: PlaceholderView, props: true },
  { path: "/jobs", component: JobsView },
  { path: "/jobs/:job_id", component: PlaceholderView, props: true },
  { path: "/dlq", component: DlqView },
  { path: "/admin/audit", component: PlaceholderView, props: { title: "Audit" } }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});
