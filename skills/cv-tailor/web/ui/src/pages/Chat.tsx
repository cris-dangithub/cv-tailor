import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowUp, Check, ChevronRight, Plus, Square, Trash2, X } from "lucide-react";
import { Fragment, useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Empty, Failed, Loading, rowIn, ThreadState } from "../components/Bits";
import { Markdown } from "../components/Markdown";
import { EffortSwitch } from "../components/Segmented";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api } from "../lib/api";
import { ago, cx, folio } from "../lib/format";
import { useStream } from "../lib/live";
import type { Msg, PermissionCard, Thread, ThreadDetail } from "../lib/types";

function useMedia(query: string) {
  return useSyncExternalStore(
    (cb) => {
      const m = window.matchMedia(query);
      m.addEventListener("change", cb);
      return () => m.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
  );
}

export function Chat() {
  const { tid } = useParams();
  const wide = useMedia("(min-width: 960px)");
  if (!wide) return tid ? <Conversation key={tid} tid={tid} /> : <ThreadList />;
  return (
    <div className="chat">
      <ThreadList active={tid} />
      <div className="chat-pane">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={tid ?? "none"}
            className="chat-pane-inner"
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0, transition: { duration: 0.26, ease: [0.16, 1, 0.3, 1] } }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }}
          >
            {tid ? <Conversation tid={tid} /> : <Conversation tid="new" />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ list
function ThreadList({ active }: { active?: string }) {
  const { t, lang } = useI18n();
  const q = useQuery({ queryKey: ["threads"], queryFn: api.threads });
  return (
    <section className="threads" aria-labelledby="threads-title">
      <header className="threads-head">
        <h1 id="threads-title" className="display threads-title">
          {t("chat.title")}
        </h1>
        <Link to="/chat/new" className="btn small" aria-label={t("chat.new")}>
          <Plus size={15} strokeWidth={1.7} aria-hidden />
          <span className="threads-new-label">{t("chat.new")}</span>
        </Link>
      </header>
      {q.isLoading ? (
        <Loading rows={5} />
      ) : q.isError ? (
        <Failed q={q} />
      ) : !q.data?.length ? (
        <Empty>{t("chat.noThreads")}</Empty>
      ) : (
        <ul className="thread-list">
          <AnimatePresence initial={false}>
            {q.data.map((th, i) => (
              <motion.li key={th.id} layout="position" {...rowIn(i)}>
                <Link to={`/chat/${th.id}`} className={cx("thread-row", active === th.id && "on", th.unread && "unread")}>
                  <span className="thread-top">
                    <span className="thread-title">{th.title}</span>
                    {th.unread && th.status !== "running" && <span className="nav-dot" aria-hidden />}
                  </span>
                  <span className="thread-meta">
                    <ThreadState status={th.status} />
                    {th.app_id && <span className="num small">{folio(th.app_id)}</span>}
                    <span className="muted small">{ago(th.updated, lang)}</span>
                  </span>
                  {th.status === "running" && <span className="working-line" aria-hidden />}
                </Link>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ conversation
type Item =
  | { kind: "msg"; msg: Msg }
  | { kind: "work"; id: string; steps: { name: string; summary: string; error: boolean; done: boolean }[] }
  | { kind: "perm"; card: PermissionCard; decision: boolean | null; id: string };

function toItems(messages: Msg[]): Item[] {
  const out: Item[] = [];
  const decisions = new Map<string, boolean>();
  const results = new Map<string, boolean>();
  for (const m of messages) {
    if (m.role === "decision") decisions.set(m.request_id, m.allow);
    if (m.role === "tool_result") results.set(m.tool_use_id, m.is_error);
  }
  for (const m of messages) {
    if (m.role === "tool") {
      const last = out[out.length - 1];
      const step = { name: m.name, summary: m.summary, error: results.get(m.tool_use_id) === true, done: results.has(m.tool_use_id) };
      if (last?.kind === "work") last.steps.push(step);
      else out.push({ kind: "work", id: m.id, steps: [step] });
    } else if (m.role === "permission") {
      out.push({ kind: "perm", id: m.id, card: m, decision: decisions.has(m.request_id) ? decisions.get(m.request_id)! : null });
    } else if (m.role !== "tool_result" && m.role !== "decision") {
      out.push({ kind: "msg", msg: m });
    }
  }
  return out;
}

function Conversation({ tid }: { tid: string }) {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isNew = tid === "new";
  const q = useQuery({ queryKey: ["thread", tid], queryFn: () => api.thread(tid), enabled: !isNew });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const stream = useStream(isNew ? undefined : tid);
  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const items = useMemo(() => toItems(q.data?.messages ?? []), [q.data?.messages]);
  const th = q.data;
  const busy = th?.status === "running" || th?.status === "queued";

  // keep the newest line in view while the user is at the bottom
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [items.length, stream.length, th?.status]);

  useEffect(() => {
    if (th?.unread) qc.invalidateQueries({ queryKey: ["threads"] });
  }, [th?.unread, qc]);

  const del = useMutation({
    mutationFn: () => api.deleteThread(tid),
    onSuccess: () => {
      qc.setQueryData<Thread[]>(["threads"], (l) => l?.filter((x) => x.id !== tid));
      navigate("/chat");
    },
  });

  if (!isNew && q.isLoading) return <Loading rows={6} />;
  if (!isNew && (q.isError || !th)) return <Failed q={q} />;

  return (
    <section className="convo">
      <header className="convo-head">
        <Link to="/chat" className="convo-back btn quiet small icon" aria-label={t("chat.back")}>
          <ArrowLeft size={17} strokeWidth={1.6} />
        </Link>
        <div className="convo-heading">
          <h2 className="display convo-title">{isNew ? t("chat.new") : th!.title}</h2>
          {th && (
            <p className="convo-meta">
              <ThreadState status={th.status} />
              <span className="muted small">{t(`kind.${th.kind}` as Key)}</span>
              {th.app_id && (
                <Link to={`/applications/${th.app_id}`} className="link small">
                  {t("chat.openApp", { id: folio(th.app_id) })}
                </Link>
              )}
              {th.usage.input_tokens + th.usage.output_tokens > 0 && (
                <span className="muted small tabular">
                  {t("chat.tokens", { n: (th.usage.input_tokens + th.usage.output_tokens).toLocaleString(lang) })}
                </span>
              )}
            </p>
          )}
        </div>
        {th && (
          <button
            type="button"
            className="btn quiet small icon"
            aria-label={t("chat.delete")}
            title={t("chat.delete")}
            onClick={() => window.confirm(t("chat.deleteConfirm")) && del.mutate()}
          >
            <Trash2 size={16} strokeWidth={1.6} />
          </button>
        )}
      </header>
      {busy && <div className="working-line convo-working" aria-hidden />}

      <div
        className="convo-scroll"
        ref={scroller}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
      >
        <div className="convo-column" aria-live="polite">
          {isNew && <p className="convo-empty">{t("chat.placeholderNew")}</p>}
          {items.map((it, i) => (
            <Fragment key={it.kind === "msg" ? it.msg.id : it.id}>
              <motion.div initial={i >= items.length - 2 ? { opacity: 0, y: 6 } : false} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 300, damping: 30 }}>
                {it.kind === "msg" ? <Message msg={it.msg} /> : it.kind === "work" ? <WorkNotes steps={it.steps} live={busy && i === items.length - 1} /> : <Permission card={it.card} decision={it.decision} />}
              </motion.div>
            </Fragment>
          ))}
          {stream.length > 0 && (
            <div className="msg-assistant live">
              <p>
                {stream.map((chunk, i) => (
                  <span key={i} className="chunk">
                    {chunk}
                  </span>
                ))}
                <span className="caret" aria-hidden />
              </p>
            </div>
          )}
          {th?.status === "queued" && <p className="convo-note">{t("chat.queued")}</p>}
          {busy && stream.length === 0 && th?.status === "running" && <p className="convo-note thinking">{t("chat.working")}</p>}
        </div>
      </div>

      <Composer tid={tid} thread={th} defaultEffort={settings.data?.effort ?? "high"} />
    </section>
  );
}

function Message({ msg }: { msg: Msg }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  if (msg.role === "user") {
    const long = msg.text.length > 600;
    return (
      <div className="msg-user">
        <span className="msg-who">{t("chat.you")}</span>
        <p className={cx(long && !open && "clamped")}>{msg.text}</p>
        {long && (
          <button type="button" className="link small" onClick={() => setOpen((o) => !o)}>
            {open ? "−" : "+"}
          </button>
        )}
      </div>
    );
  }
  if (msg.role === "assistant") return <Markdown text={msg.text} className="msg-assistant" />;
  if (msg.role === "event") {
    const text =
      msg.kind === "compacted" ? t("chat.compacted") : msg.kind === "interrupted" ? t("chat.interrupted") : msg.kind === "auth" ? t("chat.auth") : `${t("chat.error")}: ${msg.text ?? ""}`;
    return <p className={cx("msg-event", (msg.kind === "error" || msg.kind === "auth") && "error")}>{text}</p>;
  }
  return null;
}

function WorkNotes({ steps, live }: { steps: { name: string; summary: string; error: boolean; done: boolean }[]; live: boolean }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const last = steps[steps.length - 1];
  return (
    <div className={cx("work", open && "open")}>
      <button type="button" className="work-toggle" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ type: "spring", stiffness: 400, damping: 30 }} style={{ display: "inline-flex" }}>
          <ChevronRight size={14} strokeWidth={1.8} />
        </motion.span>
        <span className="work-count">{t("chat.steps", { n: steps.length })}</span>
        {!open && (
          <span className="work-last">
            {last.name} {last.summary && `· ${last.summary}`}
          </span>
        )}
        {live && !last.done && <span className="nav-pulse" aria-hidden />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.ol
            className="work-steps"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0, transition: { duration: 0.15 } }}
            transition={{ type: "spring", stiffness: 260, damping: 32 }}
          >
            {steps.map((s, i) => (
              <li key={i} className={cx(s.error && "error")}>
                <span className="work-tool">{s.name}</span>
                <span className="work-summary mono">{s.summary}</span>
              </li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </div>
  );
}

function Permission({ card, decision }: { card: PermissionCard; decision: boolean | null }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [remember, setRemember] = useState(false);
  const answer = useMutation({
    mutationFn: (allow: boolean) => api.answer(card.request_id, allow, allow && remember),
    onSettled: () => qc.invalidateQueries({ queryKey: ["thread"] }),
  });
  const settled = decision !== null || answer.isSuccess;
  const result = decision ?? answer.variables ?? null;
  return (
    <div className={cx("perm", settled && "settled")} role="group" aria-label={t("chat.permTitle")}>
      <p className="perm-title">{card.title || t("chat.permTitle")}</p>
      <p className="perm-tool">
        <span className="work-tool">{card.tool}</span>
      </p>
      {card.summary && <pre className="perm-summary mono">{card.summary}</pre>}
      {settled ? (
        <p className={cx("perm-result", result ? "ok" : "no")}>
          {result ? <Check size={15} strokeWidth={1.8} aria-hidden /> : <X size={15} strokeWidth={1.8} aria-hidden />}
          {result ? t("chat.allowed") : t("chat.denied")}
        </p>
      ) : (
        <div className="perm-actions">
          <label className="check">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            {t("chat.remember")}
          </label>
          <div className="perm-buttons">
            <button type="button" className="btn small" disabled={answer.isPending} onClick={() => answer.mutate(false)}>
              {t("chat.deny")}
            </button>
            <button type="button" className="btn accent small" disabled={answer.isPending} onClick={() => answer.mutate(true)}>
              {t("chat.allow")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Composer({ tid, thread, defaultEffort }: { tid: string; thread?: ThreadDetail; defaultEffort: string }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [effort, setEffort] = useState<string | null>(null);
  const area = useRef<HTMLTextAreaElement>(null);
  const isNew = tid === "new";
  const busy = thread?.status === "running" || thread?.status === "queued";
  const eff = effort ?? thread?.effort ?? defaultEffort;
  const touch = useMedia("(hover: none)");

  useLayoutEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight + 2, 260)}px`;
  }, [text]);

  const send = useMutation({
    mutationFn: () => (isNew ? api.newThread(text, eff) : api.send(tid, text, eff)),
    onSuccess: (th) => {
      setText("");
      qc.invalidateQueries({ queryKey: ["threads"] });
      qc.invalidateQueries({ queryKey: ["thread", th.id] });
      if (isNew) navigate(`/chat/${th.id}`, { replace: true });
    },
  });
  const stop = useMutation({ mutationFn: () => api.stop(tid) });

  return (
    <form
      className="composer-chat"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim() && !send.isPending) send.mutate();
      }}
    >
      <textarea
        ref={area}
        className="composer-input"
        rows={1}
        value={text}
        autoFocus={!touch}
        placeholder={t("chat.placeholder")}
        aria-label={t("chat.placeholder")}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !touch && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (text.trim() && !send.isPending) send.mutate();
          }
        }}
      />
      <div className="composer-row">
        <EffortSwitch value={eff} onChange={setEffort} t={t as never} />
        <div className="composer-buttons">
          {busy && (
            <button type="button" className="btn small" onClick={() => stop.mutate()} disabled={stop.isPending}>
              <Square size={12} strokeWidth={2} fill="currentColor" aria-hidden />
              {t("chat.stop")}
            </button>
          )}
          <button type="submit" className="btn primary small icon" aria-label={t("chat.send")} disabled={!text.trim() || send.isPending}>
            <ArrowUp size={17} strokeWidth={1.8} />
          </button>
        </div>
      </div>
      {send.isError && <p className="form-error">{(send.error as Error).message}</p>}
    </form>
  );
}
