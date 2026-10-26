// One Server-Sent Events stream for the whole app. The server announces what changed; the
// query cache is patched or invalidated so every screen follows the agent live.
import { QueryClient } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import type { Msg, Thread, ThreadDetail } from "./types";

type Listener = () => void;

// ------------------------------------------------------------------ streaming text per thread
const streams = new Map<string, string[]>();
const streamListeners = new Set<Listener>();
const notifyStreams = () => streamListeners.forEach((l) => l());

export function useStream(threadId: string | undefined): string[] {
  return useSyncExternalStore(
    (l) => {
      streamListeners.add(l);
      return () => streamListeners.delete(l);
    },
    () => (threadId ? streams.get(threadId) ?? EMPTY : EMPTY),
  );
}
const EMPTY: string[] = [];

// ------------------------------------------------------------------ connection state
let connected = false;
const connListeners = new Set<Listener>();
export function useConnected() {
  return useSyncExternalStore(
    (l) => {
      connListeners.add(l);
      return () => connListeners.delete(l);
    },
    () => connected,
  );
}
const setConnected = (v: boolean) => {
  if (v !== connected) {
    connected = v;
    connListeners.forEach((l) => l());
  }
};

// ------------------------------------------------------------------ notices (ticker)
export interface Notice {
  id: number;
  text: string;
  href?: string;
}
let notices: Notice[] = [];
let noticeSeq = 0;
const noticeListeners = new Set<Listener>();
export function notify(text: string, href?: string) {
  const n = { id: ++noticeSeq, text, href };
  notices = [...notices.slice(-2), n];
  noticeListeners.forEach((l) => l());
  setTimeout(() => {
    notices = notices.filter((x) => x.id !== n.id);
    noticeListeners.forEach((l) => l());
  }, 6000);
}
export function useNotices() {
  return useSyncExternalStore(
    (l) => {
      noticeListeners.add(l);
      return () => noticeListeners.delete(l);
    },
    () => notices,
  );
}

// ------------------------------------------------------------------ the stream
export function connectLive(qc: QueryClient, onThreadFinished: (t: Thread, before: Thread | undefined) => void) {
  let es: EventSource | null = null;
  let retry = 1000;
  let closed = false;

  const open = () => {
    es = new EventSource("/api/events");
    es.addEventListener("hello", () => {
      retry = 1000;
      setConnected(true);
      qc.invalidateQueries(); // whatever happened while we were away
    });
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      switch (ev.type) {
        case "apps":
          qc.invalidateQueries({ queryKey: ["applications"] });
          qc.invalidateQueries({ queryKey: ["application"] });
          qc.invalidateQueries({ queryKey: ["pdfs"] });
          qc.invalidateQueries({ queryKey: ["workspace"] });
          break;
        case "workspace":
          qc.invalidateQueries({ queryKey: ["workspace"] });
          qc.invalidateQueries({ queryKey: ["styles"] });
          break;
        case "health":
          qc.invalidateQueries({ queryKey: ["health"] });
          break;
        case "users":
          qc.invalidateQueries({ queryKey: ["users"] });
          qc.invalidateQueries({ queryKey: ["me"] });
          break;
        case "threads":
          qc.invalidateQueries({ queryKey: ["threads"] });
          break;
        case "thread": {
          const t: Thread = ev.thread;
          const before = qc.getQueryData<Thread[]>(["threads"])?.find((x) => x.id === t.id);
          qc.setQueryData<Thread[]>(["threads"], (list) => {
            if (!list) return list;
            const rest = list.filter((x) => x.id !== t.id);
            return [t, ...rest];
          });
          qc.setQueryData<ThreadDetail>(["thread", t.id], (d) => (d ? { ...d, ...t } : d));
          if (t.status !== "running" && t.status !== "queued") {
            streams.delete(t.id);
            notifyStreams();
          }
          onThreadFinished(t, before);
          break;
        }
        case "message": {
          const m: Msg = ev.message;
          qc.setQueryData<ThreadDetail>(["thread", ev.thread], (d) =>
            d && !d.messages.some((x) => x.id === m.id) ? { ...d, messages: [...d.messages, m] } : d,
          );
          if (m.role === "assistant" || m.role === "tool") {
            streams.delete(ev.thread);
            notifyStreams();
          }
          break;
        }
        case "delta": {
          const cur = streams.get(ev.thread) ?? [];
          streams.set(ev.thread, [...cur, ev.text]);
          notifyStreams();
          break;
        }
        case "permission":
          qc.invalidateQueries({ queryKey: ["thread", ev.thread] });
          break;
      }
    };
    es.onerror = () => {
      setConnected(false);
      es?.close();
      if (!closed) setTimeout(open, (retry = Math.min(retry * 2, 15000)));
    };
  };
  open();
  return () => {
    closed = true;
    es?.close();
  };
}
