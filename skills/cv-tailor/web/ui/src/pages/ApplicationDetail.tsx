import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { ArrowLeft, ArrowUpRight, Download, FolderOpen } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Empty, Failed, Loading, StatusWord, ThreadState } from "../components/Bits";
import { Markdown } from "../components/Markdown";
import { PdfSheet } from "../components/PdfSheet";
import { Route } from "../components/Route";
import { EffortSwitch, Segmented } from "../components/Segmented";
import { StatusMenu } from "../components/StatusMenu";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api, fileUrl } from "../lib/api";
import { ago, cx, folio, langName, shortDate } from "../lib/format";
import { notify } from "../lib/live";
import type { AppDetail, Pdf } from "../lib/types";

type Tab = "documents" | "report" | "offer" | "positioning" | "feedback";

export function ApplicationDetail() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["application", id], queryFn: () => api.application(id) });
  if (q.isLoading) return <Loading rows={5} />;
  if (q.isError || !q.data) return <Failed q={q} />;
  return <Detail app={q.data} />;
}

function Detail({ app }: { app: AppDetail }) {
  const { t, lang } = useI18n();
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const tabs = useMemo(
    () =>
      (["documents", "report", "offer", "positioning", "feedback"] as Tab[]).filter((k) => k === "documents" || !!app[k]),
    [app],
  );
  const [tab, setTab] = useState<Tab>("documents");

  return (
    <article className="detail">
      <Link to="/applications" className="back link small">
        <ArrowLeft size={14} strokeWidth={1.7} aria-hidden />
        {t("detail.back")}
      </Link>

      <header className="detail-head">
        <motion.span className="num detail-num" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 160, damping: 22 }}>
          {folio(app.id)}
        </motion.span>
        <div className="detail-titles">
          <h1 className="display detail-company">{app.company || "—"}</h1>
          <p className="detail-role">{app.role}</p>
          <p className="detail-meta muted small">
            {[app.location, shortDate(app.date, lang), app.languages.map((l) => l.toUpperCase()).join(" · "), t("detail.style", { name: app.style })]
              .filter(Boolean)
              .map((x, i) => (
                <span key={i}>{x}</span>
              ))}
            {app.url && (
              <a href={app.url} target="_blank" rel="noreferrer noopener" className="link">
                {t("detail.offerLink")}
                <ArrowUpRight size={13} strokeWidth={1.7} aria-hidden style={{ display: "inline", verticalAlign: "-2px" }} />
              </a>
            )}
          </p>
        </div>
      </header>

      <div className="detail-route">
        <Route status={app.status} history={app.status_history} size="large" />
        <div className="detail-route-status">
          <StatusMenu app={app} />
        </div>
      </div>

      <div className="detail-body">
        <section className="detail-main">
          {tabs.length > 1 && (
            <LayoutGroup id="detail-tabs">
              <div className="filter-tabs" role="tablist">
                {tabs.map((k) => (
                  <button key={k} type="button" role="tab" aria-selected={tab === k} className={cx("filter-tab", tab === k && "on")} onClick={() => setTab(k)}>
                    <span>{t(`detail.tab.${k}` as Key)}</span>
                    {tab === k && <motion.span layoutId="detail-tab-mark" className="filter-mark" transition={{ type: "spring", stiffness: 500, damping: 40 }} />}
                  </button>
                ))}
              </div>
            </LayoutGroup>
          )}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.24, ease: [0.16, 1, 0.3, 1] } }}
              exit={{ opacity: 0, transition: { duration: 0.1 } }}
            >
              {tab === "documents" ? (
                <Documents app={app} />
              ) : (
                <Markdown text={(app[tab] as string) || ""} className="detail-prose" />
              )}
            </motion.div>
          </AnimatePresence>
        </section>

        <aside className="detail-margin">
          <section className="margin-block margin-status">
            <h2 className="margin-title">{t("apps.changeStatus")}</h2>
            <StatusMenu app={app} />
          </section>

          <Feedback app={app} />

          <section className="margin-block">
            <h2 className="margin-title">{t("detail.history")}</h2>
            <ol className="history">
              {[...app.status_history].reverse().map((h, i) => (
                <li key={i}>
                  <StatusWord status={h.status} />
                  <span className="muted small tabular">{shortDate(h.date, lang)}</span>
                  {h.note && <p className="history-note">{h.note}</p>}
                </li>
              ))}
            </ol>
          </section>

          {app.versions?.length > 1 && (
            <section className="margin-block">
              <h2 className="margin-title">{t("detail.versions")}</h2>
              <ol className="history">
                {[...app.versions].reverse().map((v) => (
                  <li key={v.v}>
                    <span className="num">v{v.v}</span>
                    <span className="muted small tabular">{shortDate(v.date, lang)}</span>
                    {v.note && <p className="history-note">{v.note}</p>}
                  </li>
                ))}
              </ol>
            </section>
          )}

          {app.threads.length > 0 && (
            <section className="margin-block">
              <h2 className="margin-title">{t("detail.conversations")}</h2>
              <ul className="margin-threads">
                {app.threads.map((th) => (
                  <li key={th.id}>
                    <Link to={`/chat/${th.id}`} className="link">
                      {t(`kind.${th.kind}` as Key)}
                    </Link>
                    <ThreadState status={th.status} />
                    <span className="muted small">{ago(th.updated, lang)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {ws.data?.local && (
            <button type="button" className="btn small" onClick={() => api.openFolder(app.id)}>
              <FolderOpen size={15} strokeWidth={1.6} aria-hidden />
              {t("detail.openFolder")}
            </button>
          )}
        </aside>
      </div>
    </article>
  );
}

function Documents({ app }: { app: AppDetail }) {
  const { t, lang } = useI18n();
  const langs = [...new Set(app.pdfs.map((p) => p.lang).filter(Boolean))] as string[];
  const [pick, setPick] = useState<string>(langs[0] ?? "");
  useEffect(() => {
    if (!langs.includes(pick) && langs[0]) setPick(langs[0]);
  }, [langs.join(","), pick]); // eslint-disable-line react-hooks/exhaustive-deps

  const versions = app.pdfs.filter((p) => p.lang === pick).sort((a, b) => b.version - a.version);
  const [vName, setVName] = useState<string | null>(null);
  const shown: Pdf | undefined = versions.find((v) => v.name === vName) ?? versions.find((v) => v.current) ?? versions[0];

  if (!app.pdfs.length) return <Empty>{t("detail.noPdf")}</Empty>;

  return (
    <div className="docs-view">
      <div className="docs-bar">
        {langs.length > 1 && (
          <Segmented label={t("detail.tab.documents")} value={pick} onChange={(v) => (setPick(v), setVName(null))} options={langs.map((l) => ({ value: l, label: langName(l, lang) }))} />
        )}
        {versions.length > 1 && (
          <select className="select compact" value={shown?.name} onChange={(e) => setVName(e.target.value)} aria-label={t("detail.versions")}>
            {versions.map((v) => (
              <option key={v.name} value={v.name}>
                v{v.version}
                {v.current ? ` · ${t("detail.current")}` : ""}
              </option>
            ))}
          </select>
        )}
        {shown && (
          <a className="btn small" href={fileUrl(app.id, shown.name, true)} download>
            <Download size={15} strokeWidth={1.6} aria-hidden />
            {t("detail.download")}
          </a>
        )}
      </div>
      {shown && (
        <>
          <PdfFacts pdf={shown} />
          <PdfSheet url={fileUrl(app.id, shown.name)} label={shown.name} />
        </>
      )}
    </div>
  );
}

export function PdfFacts({ pdf }: { pdf: Pdf }) {
  const { t } = useI18n();
  const facts: { text: string; warn?: boolean }[] = [];
  if (pdf.pages) facts.push({ text: t("detail.pages", { n: pdf.pages }) });
  if (pdf.fits === true) facts.push({ text: t("detail.fits") });
  if (pdf.fits === false) facts.push({ text: t("detail.overflows"), warn: true });
  if (pdf.pending) facts.push({ text: t("detail.pendingMarks", { n: pdf.pending }), warn: true });
  if (pdf.broken_links) facts.push({ text: t("detail.brokenLinks", { n: pdf.broken_links }), warn: true });
  if (!facts.length) return null;
  return (
    <p className="pdf-facts small">
      {facts.map((f, i) => (
        <span key={i} className={cx(f.warn && "warn")}>
          {f.text}
        </span>
      ))}
    </p>
  );
}

function Feedback({ app }: { app: AppDetail }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const [text, setText] = useState("");
  const [effort, setEffort] = useState<string | null>(null);
  const send = useMutation({
    mutationFn: () => api.feedback(app.id, text, effort ?? settings.data?.effort),
    onSuccess: (th) => {
      setText("");
      notify(t("detail.feedbackSent"), `/chat/${th.id}`);
      navigate(`/chat/${th.id}`);
    },
  });
  return (
    <section className="margin-block">
      <h2 className="margin-title">{t("detail.giveFeedback")}</h2>
      <form
        className="feedback"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) send.mutate();
        }}
      >
        <textarea className="textarea" rows={4} value={text} placeholder={t("detail.feedbackPlaceholder")} onChange={(e) => setText(e.target.value)} />
        <div className="feedback-bar">
          <EffortSwitch value={effort ?? settings.data?.effort ?? "high"} onChange={setEffort} t={t as never} />
          <button type="submit" className="btn primary small" disabled={!text.trim() || send.isPending}>
            {t("detail.sendFeedback")}
          </button>
        </div>
        {send.isError && <p className="form-error">{(send.error as Error).message}</p>}
      </form>
    </section>
  );
}
