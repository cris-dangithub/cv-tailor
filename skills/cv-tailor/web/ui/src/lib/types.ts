export type Status = "generated" | "sent" | "replied" | "interview" | "rejected" | "offer" | "withdrawn";

export interface StatusEntry {
  status: Status;
  date: string;
  note: string;
}

export interface Version {
  v: number;
  date: string;
  note: string;
}

export interface AppRow {
  id: string;
  company: string;
  role: string;
  location: string;
  url: string;
  date: string;
  languages: string[];
  style: string;
  status: Status;
  keywords: string[];
  summary: string;
  status_history: StatusEntry[];
  versions: Version[];
  updated?: string;
  folder: string;
  pdfs: number;
}

export interface Pdf {
  name: string;
  lang: string | null;
  version: number;
  current: boolean;
  size: number;
  modified: number;
  pages: number | null;
  fits: boolean | null;
  broken_links: number;
  pending: number;
}

export interface PdfRow extends Pdf {
  app_id: string;
  company: string;
  role: string;
  status: Status;
  date: string;
}

export type ThreadKind = "offer" | "chat" | "feedback" | "style";
export type ThreadStatus = "queued" | "running" | "waiting" | "idle" | "error" | "stopped";

export interface Thread {
  id: string;
  kind: ThreadKind;
  title: string;
  app_id: string | null;
  session_id: string | null;
  status: ThreadStatus;
  effort: string;
  created: string;
  updated: string;
  unread: boolean;
  preview: string;
  error: string | null;
  usage: { input_tokens: number; output_tokens: number; cost_usd: number };
}

export interface PermissionCard {
  request_id: string;
  tool: string;
  summary: string;
  title: string;
  rule: string;
}

interface Base {
  id: string;
  ts: string;
}

export type Msg =
  | (Base & { role: "user"; text: string; effort?: string })
  | (Base & { role: "assistant"; text: string })
  | (Base & { role: "tool"; tool_use_id: string; name: string; summary: string })
  | (Base & { role: "tool_result"; tool_use_id: string; is_error: boolean; text: string })
  | (Base & { role: "permission" } & PermissionCard)
  | (Base & { role: "decision"; request_id: string; allow: boolean })
  | (Base & { role: "event"; kind: "compacted" | "error" | "interrupted" | "auth"; text?: string });

export interface ThreadDetail extends Thread {
  messages: Msg[];
  pending: PermissionCard[];
}

export interface AppDetail extends Omit<AppRow, "pdfs"> {
  pdfs: Pdf[];
  report: string | null;
  feedback: string | null;
  offer: string | null;
  positioning: string | null;
  threads: Thread[];
}

export interface Workspace {
  path: string;
  name: string;
  candidate: string;
  ui_language: string;
  cv_languages: string[];
  style: string;
  statuses: Status[];
  counts: Record<Status, number>;
  total: number;
  local: boolean;
  lan: { enabled: boolean; urls: string[] } | null;
}

export interface Settings {
  model: string;
  effort: string;
  autocompact: string;
  concurrency: number;
  ui_language: string | null;
  always_allow: string[];
}

export interface Style {
  name: string;
  origin: "built-in" | "workspace";
  path: string;
  description: string;
  active: boolean;
}

export interface Styles {
  active: string;
  history: { style: string; date: string }[];
  styles: Style[];
}
