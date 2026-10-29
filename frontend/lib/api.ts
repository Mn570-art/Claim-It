import type { ClaimBundle, ClaimSummary, DraftPayload } from "@/lib/types";

// Public links stay on this site. Vercel sends /api and /health to the backend service.
// Server-side calls use the BACKEND_URL binding instead of a public hostname.
export const API_URL = "";

async function endpoint(path: string): Promise<string> {
  const publicPath = path.startsWith("/") ? path : `/${path}`;
  if (typeof window !== "undefined") return publicPath;
  const { serverApiUrl } = await import("./server-backend");
  return serverApiUrl(publicPath);
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(await endpoint(path), {
      ...init,
      headers: {
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(init?.headers || {}),
      },
    });
  } catch {
    throw new ApiError(0, "network", "Claim-It API is not reachable. Locally, start the backend on port 8741.");
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new ApiError(response.status, body.error?.code || "error", body.error?.message || "The request failed.");
  }
  return body as T;
}

export function fileUrl(path: string) {
  return `${API_URL}${path}`;
}

export const api = {
  health: () => request<{ status: string; sarvam_configured: boolean }>("/health"),
  settings: () =>
    request<{
      preferred_language: "en" | "hi";
      voice_playback: boolean;
      retention_days: number;
      sarvam_configured: boolean;
      max_upload_mb: number;
      max_pdf_pages: number;
      disclaimer: string;
      privacy: string;
    }>("/api/settings"),
  updateSettings: (body: { preferred_language?: "en" | "hi"; voice_playback?: boolean }) =>
    request<Awaited<ReturnType<typeof api.settings>>>("/api/settings", { method: "PATCH", body: JSON.stringify(body) }),
  deleteAll: () => request<{ deleted: boolean }>("/api/data", { method: "DELETE" }),
  claims: () => request<{ claims: ClaimSummary[] }>("/api/claims"),
  claim: (id: string) => request<ClaimBundle>(`/api/claims/${id}`),
  createClaim: (body: Record<string, unknown>) =>
    request<ClaimBundle>("/api/claims", { method: "POST", body: JSON.stringify(body) }),
  updateClaim: (id: string, body: Record<string, unknown>) =>
    request<ClaimBundle>(`/api/claims/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteClaim: (id: string) => request(`/api/claims/${id}`, { method: "DELETE" }),
  seedDemo: (language: "en" | "hi", stage = "ready") =>
    request<ClaimBundle>(`/api/demo/seed?language=${language}&stage=${stage}`, { method: "POST" }),
  attachDemoDocuments: (id: string) => request<ClaimBundle>(`/api/claims/${id}/demo-documents`, { method: "POST" }),
  deleteDocument: (id: string) => request(`/api/documents/${id}`, { method: "DELETE" }),
  saveNarrative: (id: string, body: Record<string, unknown>) =>
    request<{ claim: ClaimBundle }>(`/api/claims/${id}/narrative`, { method: "POST", body: JSON.stringify(body) }),
  analyze: (id: string) => request<ClaimBundle>(`/api/claims/${id}/analyze`, { method: "POST" }),
  draft: (id: string, regenerate = false) =>
    request<{ draft: DraftPayload; version: number; reviewed_by_user: boolean }>(
      `/api/claims/${id}/draft?regenerate=${regenerate}`,
      { method: "POST" },
    ),
  patchDraft: (id: string, body: Partial<DraftPayload>) =>
    request<{ draft: DraftPayload; version: number; reviewed_by_user: boolean }>(`/api/claims/${id}/draft`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  recalculate: (id: string) =>
    request<{ draft: DraftPayload; version: number }>(`/api/claims/${id}/recalculate`, { method: "POST" }),
  review: (id: string) =>
    request<ClaimBundle>(`/api/claims/${id}/draft/review`, { method: "POST", body: JSON.stringify({ confirmed: true }) }),
  ready: (id: string) =>
    request<ClaimBundle>(`/api/claims/${id}/ready`, { method: "POST", body: JSON.stringify({ confirmed: true }) }),
  ask: (id: string, question: string) =>
    request<{ answer: string; citations: { quote: string; page_number: number; document_id: string }[]; engine: string; live_api_call: boolean }>(
      `/api/claims/${id}/ask`,
      { method: "POST", body: JSON.stringify({ question }) },
    ),
  transcribe: async (id: string, audio: Blob, language: "en" | "hi") => {
    const data = new FormData();
    data.append("audio", audio, "incident.wav");
    data.append("language", language);
    return request<{ transcript: string; cached: boolean; live_api_call: boolean; engine: string }>(
      `/api/claims/${id}/transcribe`,
      { method: "POST", body: data },
    );
  },
  speak: async (text: string, language: "en" | "hi") => {
    const response = await fetch(await endpoint("/api/speech/speak"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, body.error?.code || "error", body.error?.message || "Playback failed.");
    }
    return response.blob();
  },
};

export function uploadDocument(
  claimId: string,
  file: File,
  documentType: string,
  onProgress: (ratio: number) => void,
) {
  return new Promise<ClaimBundle["documents"][number]>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/claims/${claimId}/documents`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      let body: { error?: { code?: string; message?: string } } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        body = {};
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as ClaimBundle["documents"][number]);
      else reject(new ApiError(xhr.status, body.error?.code || "upload_failed", body.error?.message || "Upload failed."));
    };
    xhr.onerror = () => reject(new ApiError(0, "network", "Upload failed because the API could not be reached."));
    const data = new FormData();
    data.append("file", file);
    data.append("document_type", documentType);
    xhr.send(data);
  });
}
