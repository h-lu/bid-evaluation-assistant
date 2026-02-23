import { defineStore } from "pinia";
import { computed, ref } from "vue";

const ROLE_MATRIX = {
  admin: {
    upload: true,
    evaluate: true,
    review: true,
    dlq_requeue: true,
    dlq_discard: true,
    audit_view: true,
    projects_write: true,
    rules_write: true
  },
  agent: {
    upload: true,
    evaluate: true,
    review: true,
    dlq_requeue: true,
    dlq_discard: false,
    audit_view: false,
    projects_write: true,
    rules_write: true
  },
  evaluator: {
    upload: true,
    evaluate: true,
    review: true,
    dlq_requeue: false,
    dlq_discard: false,
    audit_view: false,
    projects_write: false,
    rules_write: false
  },
  viewer: {
    upload: false,
    evaluate: false,
    review: false,
    dlq_requeue: false,
    dlq_discard: false,
    audit_view: false,
    projects_write: false,
    rules_write: false
  }
};

export const useSessionStore = defineStore("session", () => {
  const role = ref("admin");
  const tenantId = ref("tenant_demo");

  const permissions = computed(() => ROLE_MATRIX[role.value] || ROLE_MATRIX.viewer);

  function setRole(nextRole) {
    role.value = ROLE_MATRIX[nextRole] ? nextRole : "viewer";
  }

  function setTenant(nextTenant) {
    tenantId.value = nextTenant || "tenant_demo";
  }

  function can(action) {
    return Boolean(permissions.value[action]);
  }

  return {
    role,
    tenantId,
    setRole,
    setTenant,
    can
  };
});
