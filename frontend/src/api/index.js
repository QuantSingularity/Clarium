import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: BASE, timeout: 15000 });

// ── KYC ──────────────────────────────────────────────────────────────────────
export const kyc = {
  submit: (data) => api.post("/kyc/submit", data),
  status: (userId) => api.get(`/kyc/status/${userId}`),
  queue: (params = {}) => api.get("/kyc/queue", { params }),
  review: (userId, data) => api.patch(`/kyc/review/${userId}`, data),
  upload: (userId, file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/kyc/upload/${userId}`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// ── AML ──────────────────────────────────────────────────────────────────────
export const aml = {
  check: (data) => api.post("/aml/check", data),
  flags: (params = {}) => api.get("/aml/flags", { params }),
  flag: (id) => api.get(`/aml/flags/${id}`),
  review: (id, status) => api.patch(`/aml/review/${id}?status=${status}`),
};

// ── Audit ─────────────────────────────────────────────────────────────────────
export const audit = {
  trail: (entityId, params = {}) =>
    api.get(`/audit/trail/${entityId}`, { params }),
  recent: (params = {}) => api.get("/audit/recent", { params }),
  verify: () => api.get("/audit/verify"),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const admin = {
  stats: () => api.get("/admin/stats"),
  pepList: () => api.get("/admin/pep/list"),
  addPep: (data) => api.post("/admin/pep", data),
  removePep: (id) => api.delete(`/admin/pep/${id}`),
};

// ── Rules ─────────────────────────────────────────────────────────────────────
export const rules = {
  list: () => api.get("/rules/"),
  get: (code) => api.get(`/rules/${code}`),
  checkTxn: (data) => api.post("/rules/check/transaction", data),
  reload: () => api.post("/rules/reload"),
};

// ── Webhooks ──────────────────────────────────────────────────────────────────
export const webhooks = {
  list: () => api.get("/webhooks/"),
  create: (data) => api.post("/webhooks/", data),
  remove: (id) => api.delete(`/webhooks/${id}`),
  deliveries: (id) => api.get(`/webhooks/${id}/deliveries`),
};

export default api;
