import type {
  Asset,
  AssetRequirement,
  AssetStatus,
  ContentSegment,
  ProcessingJob,
  Project,
  ProjectSummary,
} from '@/types';

/**
 * Resolves the API origin.
 *
 * NEXT_PUBLIC_API_URL is inlined at build time by Next, so it must be set in
 * the Vercel project settings (not only in .env.local). It may be given with or
 * without the trailing `/api` prefix — both forms normalise to the same origin.
 *
 * Falls back to localhost:8000 only when the variable is absent, which is the
 * local-development case. A production build without the variable set will
 * therefore fail loudly at request time rather than silently pointing nowhere.
 */
function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  let url = raw && raw.length > 0 ? raw : 'http://localhost:8000';
  url = url.replace(/\/+$/, '');
  if (!/\/api$/.test(url)) url = `${url}/api`;
  return url;
}

export const API_BASE_URL = getApiBaseUrl();

/** True when the app is pointing at a local backend. Used by the offline hint. */
export const IS_LOCAL_API = /^https?:\/\/(localhost|127\.0\.0\.1)/.test(API_BASE_URL);

const DEFAULT_TIMEOUT_MS = 20_000;

export class ApiError extends Error {
  readonly status: number;
  /** Raw server detail, kept for the console — never rendered to users. */
  readonly detail: string;

  constructor(status: number, message: string, detail = '') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }

  /** 0 means the request never reached the server. */
  get isNetworkError(): boolean {
    return this.status === 0;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }

  get isValidation(): boolean {
    return this.status === 422;
  }
}

/**
 * Turns a FastAPI error body into a single human sentence.
 * Handles the three shapes this backend produces:
 *   - HTTPException  → {"detail": "Project not found."}
 *   - Pydantic 422   → {"detail": [{loc, msg, type}, ...]}
 *   - 500 handler    → {"detail": "An unexpected server error occurred.", "type": "..."}
 */
function extractDetail(body: unknown): string {
  if (typeof body === 'string') return body;
  if (!body || typeof body !== 'object') return '';

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (!d || typeof d !== 'object') return String(d);
        const item = d as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(item.loc)
          ? item.loc.filter((p) => p !== 'body').join('.')
          : '';
        const msg = (item.msg ?? '').replace(/^Value error,\s*/i, '');
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join('; ');
  }

  return '';
}

/** Maps a status code to a message safe and useful to show in the UI. */
function friendlyMessage(status: number, detail: string): string {
  switch (status) {
    case 400:
      return detail || 'The request was rejected. Check the submitted values.';
    case 404:
      return detail || 'Not found.';
    case 409:
      return detail || 'This project is already being processed.';
    case 422:
      return detail || 'Some fields are invalid. Review the form and try again.';
    case 429:
      return 'Too many requests reached the engine. Wait a moment and retry.';
    case 500:
    case 502:
    case 503:
    case 504:
      // Deliberately generic: server internals (type names, tracebacks) stay in
      // the console via ApiError.detail and never reach the screen.
      return 'The SLAYERS engine hit a server error. Try again in a moment.';
    default:
      return detail || `Request failed (${status}).`;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...init } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...headers },
      signal: controller.signal,
      cache: 'no-store',
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(
        0,
        'The engine took too long to respond. It may still be working — reload in a moment.',
        'timeout'
      );
    }
    throw new ApiError(
      0,
      IS_LOCAL_API
        ? 'Cannot reach the SLAYERS engine at localhost:8000. Start the backend, then retry.'
        : 'Cannot reach the SLAYERS engine. Check your connection and retry.',
      err instanceof Error ? err.message : String(err)
    );
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    const detail = extractDetail(parsed);
    if (typeof console !== 'undefined') {
      console.error(`[SLAYERS API] ${response.status} ${endpoint}`, detail || text);
    }
    throw new ApiError(response.status, friendlyMessage(response.status, detail), detail || text);
  }

  return parsed as T;
}

export const api = {
  createProject: (name: string, source_text: string, source_type = 'script') =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, source_text, source_type }),
    }),

  createDemoProject: () => request<Project>('/projects/demo', { method: 'POST' }),

  listProjects: () => request<Project[]>('/projects'),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),

  startProcessing: (id: string) =>
    request<ProcessingJob>(`/projects/${id}/process`, { method: 'POST' }),

  /** Polled during processing — short timeout so a stalled poll does not pile up. */
  getProjectStatus: (id: string) =>
    request<ProcessingJob>(`/projects/${id}/status`, { timeoutMs: 8_000 }),

  getProjectSegments: (id: string) => request<ContentSegment[]>(`/projects/${id}/segments`),

  getProjectRequirements: (id: string) =>
    request<AssetRequirement[]>(`/projects/${id}/requirements`),

  getProjectAssets: (id: string) => request<Asset[]>(`/projects/${id}/assets`),

  getProjectSummary: (id: string) => request<ProjectSummary>(`/projects/${id}/summary`),

  getAsset: (id: string) => request<Asset>(`/assets/${id}`),

  updateAssetStatus: (id: string, status: AssetStatus) =>
    request<Asset>(`/assets/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
};
