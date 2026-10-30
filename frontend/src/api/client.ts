/**
 * Mujeaz API client. All calls go to the FastAPI backend (same origin; Vite/nginx proxy /api).
 * The access token is kept in sessionStorage so it is cleared when the tab closes.
 */
import type { ClaimDigitalTwin, CommandCenterMetrics } from '../types';

const TOKEN_KEY = 'mujeaz.token';
const USER_KEY = 'mujeaz.user';

export interface SessionUser {
  username: string;
  name: string;
  roles: string[];
}

export interface DemoUser {
  username: string;
  name: string;
  role: string;
}

export interface AuditEntry {
  chain_key: string;
  seq: number;
  occurred_at: string;
  actor_id: string;
  actor_role: string;
  action: string;
  details: Record<string, unknown> & {
    message?: string;
    message_ar?: string;
    actor_label?: string;
    human_gate?: string | null;
    simulated?: boolean;
  };
  prev_hash: string;
  hash: string;
}

export interface AuditVerification {
  chain_key: string;
  entries: number;
  valid: boolean;
  first_broken_seq: number | null;
  reason: string | null;
  head: string | null;
  algorithm: string;
}

export interface AnalyzeResult {
  analysis_run_id: string;
  mode: 'baseline' | 'llm';
  requested_mode: 'baseline' | 'llm';
  fallback_reason: string | null;
  policy_version: string;
  status: string;
  readiness: number;
  outcomes: Record<string, string>;
  facts: number;
  rejected_quotes: number;
  injection_flags: number;
}

export type AnalyzeEvent =
  | { event: 'start'; data: { case_id: string } }
  | { event: 'step'; data: { agent: string; status: string; [k: string]: unknown } }
  | { event: 'done'; data: AnalyzeResult }
  | { event: 'error'; data: { status: number; message: string } };

/** Parses a Server-Sent Events byte stream into events (exported for tests). */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<AnalyzeEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let event = 'message';
      const data: string[] = [];
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
      }
      if (data.length) yield { event, data: JSON.parse(data.join('\n')) } as AnalyzeEvent;
    }
    if (done) return;
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function safeStorage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export const session = {
  token(): string | null {
    return safeStorage()?.getItem(TOKEN_KEY) ?? null;
  },
  user(): SessionUser | null {
    try {
      const raw = safeStorage()?.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as SessionUser) : null;
    } catch {
      return null;
    }
  },
  set(token: string, user: SessionUser) {
    const s = safeStorage();
    s?.setItem(TOKEN_KEY, token);
    s?.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    const s = safeStorage();
    s?.removeItem(TOKEN_KEY);
    s?.removeItem(USER_KEY);
  },
};

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();
export function onUnauthorized(fn: Listener): () => void {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body) headers.set('Content-Type', 'application/json');
  const token = session.token();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401 && token) {
    session.clear();
    unauthorizedListeners.forEach((fn) => fn());
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = body?.error?.message ?? body?.detail ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  devUsers: () => request<{ users: DemoUser[] }>('/api/auth/dev-users'),
  async devLogin(username: string): Promise<SessionUser> {
    const r = await post<{ access_token: string; user: SessionUser }>('/api/auth/dev-login', { username });
    session.set(r.access_token, r.user);
    return r.user;
  },
  me: () => request<SessionUser & { permissions: string[] }>('/api/auth/me'),
  twins: () => request<{ items: ClaimDigitalTwin[] }>('/api/twins'),
  twin: (id: string) => request<ClaimDigitalTwin>(`/api/cases/${encodeURIComponent(id)}`),
  metrics: () => request<CommandCenterMetrics>('/api/metrics'),
  transition: (id: string, to: string, note?: string) =>
    post<{ id: string; from: string; to: string }>(`/api/cases/${encodeURIComponent(id)}/transitions`, { to, note }),
  evidenceHunterDemo: (id: string) =>
    post<{ found: boolean; status?: string; overallScore?: number; revenueProtected?: number }>(
      `/api/cases/${encodeURIComponent(id)}/evidence-hunter/demo`,
    ),
  audit: (id: string) => request<{ chain_key: string; entries: AuditEntry[] }>(`/api/audit/${encodeURIComponent(id)}`),
  auditVerify: (id: string) => request<AuditVerification>(`/api/audit/${encodeURIComponent(id)}/verify`),
  /** Runs A1 → A2 → A3 → A5 with streamed progress. The token stays in the Authorization header. */
  async analyzeCase(id: string, onEvent: (e: AnalyzeEvent) => void, mode?: 'baseline' | 'llm'): Promise<AnalyzeResult> {
    const headers = new Headers({ Accept: 'text/event-stream' });
    const token = session.token();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const qs = new URLSearchParams({ stream: 'true', ...(mode ? { mode } : {}) });
    const res = await fetch(`/api/cases/${encodeURIComponent(id)}/analyze?${qs}`, { method: 'POST', headers });
    if (!res.ok || !res.body) {
      let message = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        message = body?.error?.message ?? body?.detail ?? message;
      } catch {
        /* non-JSON error body */
      }
      if (res.status === 401 && token) {
        session.clear();
        unauthorizedListeners.forEach((fn) => fn());
      }
      throw new ApiError(res.status, message);
    }
    for await (const e of readSse(res.body)) {
      onEvent(e);
      if (e.event === 'done') return e.data;
      if (e.event === 'error') throw new ApiError(e.data.status, e.data.message);
    }
    throw new ApiError(500, 'Analysis stream ended unexpectedly');
  },
  analyzeOrder: (body: { clinicalNoteText: string; payerName?: string; requestedService?: string }) =>
    post<any>('/api/ai/analyze-order', body),
  generateAppeal: (body: Record<string, unknown>) => post<any>('/api/ai/generate-appeal', body),
};

export const ROLE_LABELS: Record<string, { en: string; ar: string }> = {
  physician: { en: 'Physician', ar: 'طبيب' },
  auth_officer: { en: 'Authorization Officer', ar: 'موظف الموافقات' },
  coder: { en: 'Medical Coder', ar: 'أخصائي الترميز' },
  appeals_officer: { en: 'Appeals Officer', ar: 'مسؤول الاستئنافات' },
  rcm_manager: { en: 'RCM Manager', ar: 'مدير دورة الإيرادات' },
  auditor: { en: 'Auditor', ar: 'مدقق' },
};
