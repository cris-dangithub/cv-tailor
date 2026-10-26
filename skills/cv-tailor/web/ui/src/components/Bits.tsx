import type { UseQueryResult } from "@tanstack/react-query";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { cx } from "../lib/format";
import type { Status, ThreadStatus } from "../lib/types";

export function PageHead({ title, lede, aside }: { title: ReactNode; lede?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="page-head">
      <div>
        <h1 className="display page-title">{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {aside && <div className="page-head-aside">{aside}</div>}
    </header>
  );
}

export function Loading({ rows = 4 }: { rows?: number }) {
  return (
    <div className="loading" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: 44, opacity: 1 - i * 0.15 }} />
      ))}
    </div>
  );
}

export function Failed({ q }: { q: UseQueryResult<unknown> }) {
  const { t } = useI18n();
  return (
    <div className="failed" role="alert">
      <p>{t("common.failed", { msg: (q.error as Error)?.message || "?" })}</p>
      <button type="button" className="btn small" onClick={() => q.refetch()}>
        {t("common.retry")}
      </button>
    </div>
  );
}

export function StatusWord({ status }: { status: Status }) {
  const { t } = useI18n();
  return (
    <span className="status" style={{ ["--tone" as string]: `var(--st-${status})` }}>
      {t(`status.${status}` as Key)}
    </span>
  );
}

const THREAD_TONE: Record<ThreadStatus, string> = {
  queued: "var(--ink-3)",
  running: "var(--accent)",
  waiting: "var(--accent)",
  idle: "var(--st-offer)",
  error: "var(--danger)",
  stopped: "var(--ink-3)",
};

export function ThreadState({ status }: { status: ThreadStatus }) {
  const { t } = useI18n();
  return (
    <span className={cx("status", `thread-${status}`)} style={{ ["--tone" as string]: THREAD_TONE[status] }}>
      {t(`thread.${status}` as Key)}
    </span>
  );
}

/** Rows that arrive one after another, capped so long lists do not keep the user waiting. */
export const rowIn = (i: number) => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, transition: { duration: 0.12 } },
  transition: { type: "spring" as const, stiffness: 300, damping: 30, delay: Math.min(i, 10) * 0.025 },
});

export function Empty({ children }: { children: ReactNode }) {
  return (
    <motion.p className="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {children}
    </motion.p>
  );
}
