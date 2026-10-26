import type {
  AppDetail,
  AppRow,
  Me,
  PdfRow,
  Settings,
  Status,
  Styles,
  Thread,
  ThreadDetail,
  UserRow,
  Workspace,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string, public retryAfter = 0) {
    super(message);
  }
}

/** Fired when a request finds the session gone (signed out elsewhere, disabled by the admin). */
export const UNAUTHORIZED = "cvt:unauthorized";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const r = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: isForm ? init?.headers : { "content-type": "application/json", ...init?.headers },
  });
  if (!r.ok) {
    let msg = r.statusText;
    let retry = 0;
    try {
      const body = await r.json();
      msg = body.error || body.detail || msg;
      retry = body.retry_after || 0;
    } catch {
      /* not json */
    }
    if (r.status === 401 && !path.startsWith("/api/auth/")) window.dispatchEvent(new Event(UNAUTHORIZED));
    throw new ApiError(r.status, typeof msg === "string" ? msg : JSON.stringify(msg), retry);
  }
  return r.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const fileUrl = (appId: string, name: string, download = false) =>
  `/api/applications/${encodeURIComponent(appId)}/files/${encodeURIComponent(name)}${download ? "?download=1" : ""}`;

export const api = {
  me: () => req<Me>("/api/auth/me"),
  login: (username: string, password: string) => req<Me>("/api/auth/login", json("POST", { username, password })),
  register: (username: string, password: string) =>
    req<Me | { status: "pending" }>("/api/auth/register", json("POST", { username, password })),
  logout: () => req<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  users: () => req<UserRow[]>("/api/users"),
  userAction: (name: string, action: "approve" | "reject" | "disable" | "enable" | "logout-all") =>
    req<UserRow[]>(`/api/users/${encodeURIComponent(name)}/${action}`, { method: "POST" }),
  userPassword: (name: string, password: string) =>
    req<UserRow[]>(`/api/users/${encodeURIComponent(name)}/password`, json("POST", { password })),
  deleteUser: (name: string) => req<UserRow[]>(`/api/users/${encodeURIComponent(name)}`, { method: "DELETE" }),

  workspace: () => req<Workspace>("/api/workspace"),
  health: () => req<{ cli: string | null; logged_in: boolean | null }>("/api/health"),
  settings: () => req<Settings>("/api/settings"),
  saveSettings: (s: Partial<Settings>) => req<Settings>("/api/settings", json("PUT", s)),

  applications: (q = "", status?: Status | null) => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (status) p.set("status", status);
    return req<AppRow[]>(`/api/applications?${p}`);
  },
  application: (id: string) => req<AppDetail>(`/api/applications/${id}`),
  setStatus: (id: string, status: Status, note = "") =>
    req<AppDetail>(`/api/applications/${id}/status`, json("PATCH", { status, note })),
  openFolder: (id: string) => req<{ ok: boolean }>(`/api/applications/${id}/open-folder`, { method: "POST" }),
  feedback: (id: string, text: string, effort?: string) =>
    req<Thread>(`/api/applications/${id}/feedback`, json("POST", { text, effort })),

  pdfs: () => req<PdfRow[]>("/api/pdfs"),
  zip: async (files: { app_id: string; name: string }[]) => {
    const r = await fetch("/api/pdfs/zip", { ...json("POST", { files }), headers: { "content-type": "application/json" } });
    if (!r.ok) throw new ApiError(r.status, r.statusText);
    const name = /filename="([^"]+)"/.exec(r.headers.get("content-disposition") || "")?.[1] || "cv-tailor.zip";
    return { blob: await r.blob(), name };
  },

  offers: (items: { text?: string; url?: string }[], effort?: string) =>
    req<Thread[]>("/api/offers", json("POST", { items, effort })),
  threads: () => req<Thread[]>("/api/threads"),
  thread: (id: string) => req<ThreadDetail>(`/api/threads/${id}`),
  newThread: (text: string, effort?: string, app_id?: string) =>
    req<Thread>("/api/threads", json("POST", { text, effort, app_id })),
  send: (id: string, text: string, effort?: string) =>
    req<Thread>(`/api/threads/${id}/messages`, json("POST", { text, effort })),
  stop: (id: string) => req<Thread>(`/api/threads/${id}/stop`, { method: "POST" }),
  deleteThread: (id: string) => req<{ ok: boolean }>(`/api/threads/${id}`, { method: "DELETE" }),
  answer: (requestId: string, allow: boolean, remember = false) =>
    req<{ ok: boolean }>(`/api/permissions/${requestId}`, json("POST", { allow, remember })),

  styles: () => req<Styles>("/api/styles"),
  useStyle: (name: string) => req<Styles>("/api/styles/active", json("PUT", { name })),
  styleFromSample: (file: File, name: string, effort?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    if (effort) fd.append("effort", effort);
    return req<Thread>("/api/styles/sample", { method: "POST", body: fd });
  },
};

export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
