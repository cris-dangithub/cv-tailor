import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Empty, Failed, Loading, PageHead, rowIn } from "../components/Bits";
import { Route } from "../components/Route";
import { Segmented } from "../components/Segmented";
import { STATUSES, StatusMenu, useSetStatus } from "../components/StatusMenu";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api } from "../lib/api";
import { cx, folio, shortDate } from "../lib/format";
import { keep, remember } from "../lib/theme";
import type { AppRow, Status } from "../lib/types";

type View = "list" | "board";

export function Applications() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const status = (params.get("status") as Status | null) || null;
  const [view, setView] = useState<View>(remember<View>("apps-view", "list"));
  const dq = useDeferredValue(q.trim());
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const apps = useQuery({
    queryKey: ["applications", dq, view === "board" ? null : status],
    queryFn: () => api.applications(dq, view === "board" ? null : status),
    placeholderData: keepPreviousData,
  });
  const counts = ws.data?.counts;

  const setStatusFilter = (s: Status | null) => {
    const p = new URLSearchParams(params);
    if (s) p.set("status", s);
    else p.delete("status");
    setParams(p, { replace: true });
  };

  return (
    <div className="apps">
      <PageHead
        title={t("apps.title")}
        aside={
          <Segmented<View>
            label={t("apps.title")}
            value={view}
            onChange={(v) => {
              setView(v);
              keep("apps-view", v);
            }}
            options={[
              { value: "list", label: t("apps.view.list") },
              { value: "board", label: t("apps.view.board") },
            ]}
          />
        }
      />

      <div className="apps-tools">
        {view === "list" && (
          <LayoutGroup id="status-filter">
            <div className="filter-tabs" role="tablist" aria-label={t("apps.title")}>
              {[null, ...STATUSES].map((s) => {
                const on = s === status;
                const n = s ? counts?.[s] : ws.data?.total;
                if (s && !n) return null;
                return (
                  <button key={s ?? "all"} type="button" role="tab" aria-selected={on} className={cx("filter-tab", on && "on")} onClick={() => setStatusFilter(s)}>
                    <span>{s ? t(`status.${s}` as Key) : t("apps.all")}</span>
                    <span className="filter-n tabular">{n ?? ""}</span>
                    {on && <motion.span layoutId="filter-mark" className="filter-mark" transition={{ type: "spring", stiffness: 500, damping: 40 }} />}
                  </button>
                );
              })}
            </div>
          </LayoutGroup>
        )}
        <label className="search">
          <Search size={16} strokeWidth={1.6} aria-hidden />
          <span className="sr-only">{t("apps.search")}</span>
          <input type="search" value={q} placeholder={t("apps.search")} onChange={(e) => setQ(e.target.value)} />
        </label>
      </div>

      {apps.isLoading ? (
        <Loading rows={6} />
      ) : apps.isError ? (
        <Failed q={apps} />
      ) : !apps.data?.length ? (
        <Empty>{dq ? t("apps.noMatch", { q: dq }) : t("apps.empty")}</Empty>
      ) : view === "list" ? (
        <IndexList rows={apps.data} />
      ) : (
        <Board rows={apps.data} />
      )}
    </div>
  );
}

function IndexList({ rows }: { rows: AppRow[] }) {
  const { lang } = useI18n();
  const navigate = useNavigate();
  return (
    <ol className="index">
      <AnimatePresence initial={false} mode="popLayout">
        {rows.map((a, i) => (
          <motion.li
            key={a.id}
            layout="position"
            {...rowIn(i)}
            className="index-row"
            onClick={() => navigate(`/applications/${a.id}`)}
          >
            <span className="num index-num" aria-hidden>
              {folio(a.id)}
            </span>
            <a
              className="index-main"
              href={`/applications/${a.id}`}
              onClick={(e) => {
                e.preventDefault();
                navigate(`/applications/${a.id}`);
              }}
            >
              <span className="index-company">{a.company || "—"}</span>
              <span className="index-role">{a.role}</span>
            </a>
            <span className="index-route">
              <Route status={a.status} history={a.status_history} />
            </span>
            <span className="index-status">
              <StatusMenu app={a} align="end" />
            </span>
            <span className="index-date muted small tabular">{shortDate(a.date, lang)}</span>
          </motion.li>
        ))}
      </AnimatePresence>
    </ol>
  );
}

function Board({ rows }: { rows: AppRow[] }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const set = useSetStatus();
  const [over, setOver] = useState<Status | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);

  return (
    <>
      <p className="muted small board-hint">{t("apps.dragHint")}</p>
      <LayoutGroup id="board">
        <div className="board">
          {STATUSES.map((s) => {
            const col = rows.filter((r) => r.status === s);
            return (
              <section
                key={s}
                className={cx("column", over === s && "over")}
                style={{ ["--tone" as string]: `var(--st-${s})` }}
                aria-label={t(`status.${s}` as Key)}
                onDragOver={(e) => {
                  e.preventDefault();
                  setOver(s);
                }}
                onDragLeave={() => setOver((o) => (o === s ? null : o))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(null);
                  const id = e.dataTransfer.getData("text/plain");
                  const app = rows.find((r) => r.id === id);
                  if (app && app.status !== s) set.mutate({ id, status: s, title: app.company || app.role });
                }}
              >
                <header className="column-head">
                  <span className="num column-n">{col.length}</span>
                  <span className="status">{t(`status.${s}` as Key)}</span>
                </header>
                <div className="column-body">
                  <AnimatePresence initial={false}>
                    {col.map((a) => (
                      <motion.article
                        key={a.id}
                        layoutId={`slip-${a.id}`}
                        className={cx("slip", dragging === a.id && "dragging")}
                        transition={{ type: "spring", stiffness: 380, damping: 34 }}
                      >
                        {/* native drag and drop lives on a plain element: Motion owns the drag props of its own */}
                        <div
                          className="slip-inner"
                          draggable
                          role="link"
                          tabIndex={0}
                          onDragStart={(e) => {
                            e.dataTransfer.setData("text/plain", a.id);
                            e.dataTransfer.effectAllowed = "move";
                            setDragging(a.id);
                          }}
                          onDragEnd={() => setDragging(null)}
                          onClick={() => navigate(`/applications/${a.id}`)}
                          onKeyDown={(e) => e.key === "Enter" && navigate(`/applications/${a.id}`)}
                        >
                          <span className="num slip-num">{folio(a.id)}</span>
                          <span className="slip-company">{a.company || "—"}</span>
                          <span className="slip-role">{a.role}</span>
                          <span className="slip-status">
                            <StatusMenu app={a} />
                          </span>
                        </div>
                      </motion.article>
                    ))}
                  </AnimatePresence>
                </div>
              </section>
            );
          })}
        </div>
      </LayoutGroup>
    </>
  );
}
