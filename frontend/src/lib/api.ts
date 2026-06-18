/**
 * LTIA Radar — API Client
 * Wrapper around fetch for communicating with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiResponse<T = unknown> {
  data?: T;
  total?: number;
  message?: string;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

// ── Sources ──
export const sourcesApi = {
  list: () => request<ApiResponse>("/api/sources"),
  create: (data: { url: string; name: string; source_type: string }) =>
    request<ApiResponse>("/api/sources", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<ApiResponse>(`/api/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<ApiResponse>(`/api/sources/${id}`, { method: "DELETE" }),
};

// ── Keywords ──
export const keywordsApi = {
  list: () => request<ApiResponse>("/api/keywords"),
  create: (data: { value: string }) =>
    request<ApiResponse>("/api/keywords", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<ApiResponse>(`/api/keywords/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<ApiResponse>(`/api/keywords/${id}`, { method: "DELETE" }),
};

// ── Articles ──
export const articlesApi = {
  list: (params?: Record<string, string>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<ApiResponse>(`/api/articles${query}`);
  },
  detail: (id: string) =>
    request<{ processed: Record<string, unknown>; raw_data: Record<string, unknown> }>(
      `/api/articles/${id}`
    ),
};

// ── Dashboard ──
export const dashboardApi = {
  stats: (params?: Record<string, string>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Record<string, unknown>>(`/api/dashboard/stats${query}`);
  },
  topRisks: (limit = 10) =>
    request<ApiResponse>(`/api/dashboard/top-risks?limit=${limit}`),
};

// ── Alert Rules ──
export const alertRulesApi = {
  list: () => request<ApiResponse>("/api/alert-rules"),
  create: (data: {
    rule_name: string;
    condition_query: Record<string, unknown>;
    telegram_chat_id: string;
  }) =>
    request<ApiResponse>("/api/alert-rules", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<ApiResponse>(`/api/alert-rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<ApiResponse>(`/api/alert-rules/${id}`, { method: "DELETE" }),
  test: (id: string) =>
    request<ApiResponse>(`/api/alert-rules/${id}/test`, { method: "POST" }),
};

// ── Crawler ──
export const crawlerApi = {
  trigger: () =>
    request<ApiResponse>("/api/crawler/trigger", { method: "POST" }),
};

// ── Health ──
export const healthApi = {
  check: () => request<{ status: string }>("/api/health"),
};
