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
  topRisks: (limit = 10, params?: Record<string, string>) => {
    const queryParams = new URLSearchParams({ limit: String(limit), ...params });
    return request<ApiResponse>(`/api/dashboard/top-risks?${queryParams.toString()}`);
  },
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
  trigger: (payload: { trigger_type: string; date_from?: string; date_to?: string }) =>
    request<ApiResponse>("/api/crawler/trigger", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSettings: () => request<Record<string, unknown>>("/api/crawler/settings"),
  updateSettings: (data: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/crawler/settings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getLogs: () => request<Record<string, any>>("/api/crawler/logs"),
};

// ── LLM Configs ──
export const llmConfigsApi = {
  list: () => request<ApiResponse>("/api/llm-configs"),
  create: (data: {
    provider: string;
    model_name: string;
    api_key: string;
    is_active?: boolean;
    is_default?: boolean;
    description?: string;
  }) =>
    request<ApiResponse>("/api/llm-configs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<ApiResponse>(`/api/llm-configs/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<ApiResponse>(`/api/llm-configs/${id}`, { method: "DELETE" }),
  test: (id: string) =>
    request<{ status: string; message: string; response?: string }>(
      `/api/llm-configs/${id}/test`,
      { method: "POST" }
    ),
  setDefault: (id: string) =>
    request<ApiResponse>(`/api/llm-configs/${id}/set-default`, { method: "POST" }),
};

// ── Health ──
export const healthApi = {
  check: () => request<{ status: string }>("/api/health"),
};

// ── LLM Prompts ──
export const llmPromptsApi = {
  list: () => request<ApiResponse>("/api/llm-prompts"),
  create: (data: {
    name: string;
    system_prompt: string;
    batch_system_prompt: string;
    is_active?: boolean;
  }) =>
    request<ApiResponse>("/api/llm-prompts", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<ApiResponse>(`/api/llm-prompts/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<ApiResponse>(`/api/llm-prompts/${id}`, { method: "DELETE" }),
  setActive: (id: string) =>
    request<ApiResponse>(`/api/llm-prompts/${id}/set-active`, { method: "POST" }),
};

// ── General Settings & Auth ──
export const generalApi = {
  getSettings: () => request<Record<string, unknown>>("/api/settings/general"),
  updateSettings: (data: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/settings/general", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  verifyPin: (pin: string, type: "user" | "admin") =>
    request<{ success: boolean; message?: string }>("/api/settings/verify-pin", {
      method: "POST",
      body: JSON.stringify({ pin, type }),
    }),
};
