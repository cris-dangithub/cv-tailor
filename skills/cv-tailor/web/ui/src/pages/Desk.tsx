import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Empty, PageHead, rowIn, ThreadState } from "../components/Bits";
import { Route } from "../components/Route";
import { EffortSwitch } from "../components/Segmented";
import { useI18n } from "../i18n";
import { api } from "../lib/api";
import { ago, folio, langName } from "../lib/format";
import type { Thread } from "../lib/types";

interface Draft {
  id: number;
  text: string;
}

const URL_RE = /^https?:\/\/\S+$/i;
let seq = 1;

function grow(el: HTMLTextAreaElement | null, min: number) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.max(min, el.scrollHeight + 2)}px`;
}

export function Desk() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const threads = useQuery({ queryKey: ["threads"], queryFn: api.threads });
  const apps = useQuery({ queryKey: ["applications", "", null], queryFn: () => api.applications() });
  const [drafts, setDrafts] = useState<Draft[]>([{ id: seq++, text: "" }]);
  const [effort, setEffort] = useState<string | null>(null);
  const refs = useRef(new Map<number, HTMLTextAreaElement>());
  const filled = drafts.filter((d) => d.text.trim());
  const eff = effort ?? settings.data?.effort ?? "high";

  const send = useMutation({
    mutationFn: () =>
      api.offers(
        filled.map((d) => (URL_RE.test(d.text.trim()) ? { url: d.text.trim() } : { text: d.text })),
        eff,
      ),
    onSuccess: (created) => {
      setDrafts([{ id: seq++, text: "" }]);
      qc.setQueryData<Thread[]>(["threads"], (list) => [...created, ...(list ?? [])]);
      if (created.length === 1) navigate(`/chat/${created[0].id}`);
    },
  });

  useEffect(() => {
    drafts.forEach((d, i) => grow(refs.current.get(d.id) ?? null, i === 0 ? 200 : 120));
  }, [drafts]);

  const langs = (ws.data?.cv_languages ?? []).map((c) => langName(c, lang));
  const langList = new Intl.ListFormat(lang, { type: "conjunction" }).format(langs.length ? langs : ["…"]);
  const onTable = (threads.data ?? []).filter(
    (th) =>
      th.kind !== "chat" &&
      (["queued", "running", "waiting", "error"].includes(th.status) ||
        Date.now() - new Date(th.updated).getTime() < 1000 * 60 * 60 * 8),
  );

  return (
    <div className="desk">
      <section className="desk-compose" aria-labelledby="desk-title">
        <PageHead title={<span id="desk-title">{t("home.title")}</span>} lede={t("home.lede", { langs: langList })} />
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            if (filled.length) send.mutate();
          }}
        >
          <AnimatePresence initial={false}>
            {drafts.map((d, i) => (
              <motion.div
                key={d.id}
                className="draft"
                layout
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0, transition: { duration: 0.16 } }}
                transition={{ type: "spring", stiffness: 260, damping: 30 }}
              >
                {drafts.length > 1 && (
                  <div className="draft-head">
                    <span className="num draft-num">{String(i + 1).padStart(2, "0")}</span>
                    <button
                      type="button"
                      className="btn quiet small icon"
                      aria-label={t("home.remove")}
                      onClick={() => setDrafts((ds) => ds.filter((x) => x.id !== d.id))}
                    >
                      <X size={15} strokeWidth={1.6} />
                    </button>
                  </div>
                )}
                <textarea
                  ref={(el) => {
                    if (el) refs.current.set(d.id, el);
                    else refs.current.delete(d.id);
                  }}
                  className="draft-text"
                  value={d.text}
                  placeholder={t("home.placeholder")}
                  aria-label={t("home.placeholder")}
                  autoFocus={i === 0}
                  onChange={(e) => setDrafts((ds) => ds.map((x) => (x.id === d.id ? { ...x, text: e.target.value } : x)))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && filled.length) {
                      e.preventDefault();
                      send.mutate();
                    }
                  }}
                />
              </motion.div>
            ))}
          </AnimatePresence>
          <div className="composer-bar">
            <button type="button" className="btn quiet small" onClick={() => setDrafts((ds) => [...ds, { id: seq++, text: "" }])}>
              <Plus size={15} strokeWidth={1.7} aria-hidden />
              {t("home.addAnother")}
            </button>
            <div className="composer-send">
              <EffortSwitch value={eff} onChange={setEffort} t={t as never} />
              <button type="submit" className="btn primary" disabled={!filled.length || send.isPending}>
                {send.isPending ? t("home.sending") : t("home.generate", { n: Math.max(1, filled.length) })}
                <ArrowRight size={16} strokeWidth={1.7} aria-hidden />
              </button>
            </div>
          </div>
          {send.isError && <p className="form-error">{(send.error as Error).message}</p>}
        </form>
      </section>

      <aside className="desk-side">
        <section aria-labelledby="table-title">
          <h2 id="table-title" className="side-title">
            {t("home.inProgress")}
          </h2>
          {onTable.length === 0 ? (
            <Empty>{t("home.nothingRunning")}</Empty>
          ) : (
            <ul className="table-list">
              <AnimatePresence initial={false}>
                {onTable.map((th, i) => (
                  <motion.li key={th.id} layout {...rowIn(i)}>
                    <Link to={`/chat/${th.id}`} className="table-row">
                      <span className="table-title">{th.title}</span>
                      <span className="table-meta">
                        <ThreadState status={th.status} />
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

        <section aria-labelledby="recent-title" className="recent">
          <div className="side-head">
            <h2 id="recent-title" className="side-title">
              {t("home.recent")}
            </h2>
            <Link to="/applications" className="link small">
              {t("home.seeAll")}
            </Link>
          </div>
          <ul className="recent-list">
            {(apps.data ?? []).slice(0, 6).map((a, i) => (
              <motion.li key={a.id} {...rowIn(i)}>
                <Link to={`/applications/${a.id}`} className="recent-row">
                  <span className="num recent-num">{folio(a.id)}</span>
                  <span className="recent-text">
                    <span className="recent-company">{a.company || "—"}</span>
                    <span className="muted small">{a.role}</span>
                  </span>
                  <Route status={a.status} history={a.status_history} />
                </Link>
              </motion.li>
            ))}
          </ul>
        </section>
      </aside>
    </div>
  );
}
