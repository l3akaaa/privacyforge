// Typed client for the PrivacyForge backend API.
// All detection/transformation happens server-side; this only orchestrates.

const BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";

export type Category = "pii" | "sensitive" | "quasi";

export interface Finding {
  entity_type: string;
  category: Category;
  source: string;
  field: string | null;
  row: number | null;
  start: number | null;
  end: number | null;
  value_preview: string;
  score: number | null;
  context: string | null;
  review_needed: boolean;
  sources: string[];
}

export interface DetectSummary {
  total: number;
  by_category: Record<string, number>;
  review_needed: number;
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    const msg =
      detail && typeof detail === "object" && "message" in detail
        ? (detail as { message: string }).message
        : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail: unknown,
  ) {
    super(message);
  }
}

export const api = {
  health: () => req<{ status: string; version: string; nlp_available: boolean }>("/health"),
  presets: () => req<Record<string, any>>("/presets"),
  createProject: (name: string) =>
    req<{ project_id: string; name: string }>("/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  uploadFile: async (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/projects/${projectId}/files`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const d = await res.json().catch(() => null);
      throw new ApiError(d?.detail?.message || "Upload failed", res.status, d);
    }
    return res.json() as Promise<{
      file_id: string;
      schema: any;
      preview: any;
      warnings: string[];
    }>;
  },
  detect: (projectId: string, fileId: string) =>
    req<{ findings: Finding[]; summary: DetectSummary; nlp_available: boolean }>(
      `/projects/${projectId}/detect`,
      { method: "POST", body: JSON.stringify({ file_id: fileId }) },
    ),
  testRule: (projectId: string, rule: any, sample: string) =>
    req<{ matches: any[] }>(`/projects/${projectId}/custom-rules/test`, {
      method: "POST",
      body: JSON.stringify({ rule, sample }),
    }),
  getPolicy: (projectId: string) =>
    req<{ policy: any }>(`/projects/${projectId}/policy`),
  setPolicy: (projectId: string, body: { policy?: any; preset_name?: string }) =>
    req<{ policy: any }>(`/projects/${projectId}/policy`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  transform: (projectId: string, fileId: string) =>
    req<{
      change_count: number;
      operators_used: Record<string, string>;
      preview_before: any;
      preview_after: any;
    }>(`/projects/${projectId}/transform`, {
      method: "POST",
      body: JSON.stringify({ file_id: fileId }),
    }),
  verify: (projectId: string, fileId: string, quasi: string[]) =>
    req<{
      risk_report: any;
      quality_report: any;
      gate: "pass" | "block";
      reasons: string[];
    }>(`/projects/${projectId}/verify`, {
      method: "POST",
      body: JSON.stringify({ file_id: fileId, quasi_identifiers: quasi }),
    }),
  exportData: (projectId: string, fileId: string, override = false) =>
    req<{ export: any; override_used: boolean; audit: any }>(
      `/projects/${projectId}/export`,
      { method: "POST", body: JSON.stringify({ file_id: fileId, override }) },
    ),
};
