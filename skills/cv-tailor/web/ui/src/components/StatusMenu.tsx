import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { api } from "../lib/api";
import { cx } from "../lib/format";
import { notify } from "../lib/live";
import type { AppRow, Status } from "../lib/types";

export const STATUSES: Status[] = ["generated", "sent", "replied", "interview", "offer", "rejected", "withdrawn"];

export function useSetStatus() {
  const qc = useQueryClient();
  const { t } = useI18n();
  return useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: Status; note?: string; title?: string }) =>
      api.setStatus(id, status, note),
    onMutate: async ({ id, status }) => {
      // the row moves at once; the server confirms a moment later
      await qc.cancelQueries({ queryKey: ["applications"] });
      const snapshots = qc.getQueriesData<AppRow[]>({ queryKey: ["applications"] });
      for (const [key, rows] of snapshots)
        if (rows)
          qc.setQueryData<AppRow[]>(key, rows.map((r) =>
            r.id === id ? { ...r, status, status_history: [...(r.status_history || []), { status, date: new Date().toISOString().slice(0, 10), note: "" }] } : r,
          ));
      return { snapshots };
    },
    onError: (_e, _v, ctx) => ctx?.snapshots.forEach(([k, rows]) => qc.setQueryData(k, rows)),
    onSuccess: (_d, v) => {
      if (v.title) notify(t("apps.moved", { title: v.title, status: t(`status.${v.status}` as never) }));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application"] });
      qc.invalidateQueries({ queryKey: ["workspace"] });
    },
  });
}

export function StatusMenu({ app, align = "start" }: { app: Pick<AppRow, "id" | "status" | "company" | "role">; align?: "start" | "end" }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState<Status>(app.status);
  const [note, setNote] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const set = useSetStatus();

  useEffect(() => {
    if (!open) return;
    setPick(app.status);
    setNote("");
    const onDown = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, app.status]);

  const save = () => {
    set.mutate({ id: app.id, status: pick, note, title: app.company || app.role });
    setOpen(false);
  };

  return (
    <div className="status-menu" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className="status-trigger"
        style={{ ["--tone" as string]: `var(--st-${app.status})` }}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`${t("apps.changeStatus")}: ${t(`status.${app.status}` as never)}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="status">{t(`status.${app.status}` as never)}</span>
        <ChevronDown size={14} strokeWidth={1.75} aria-hidden />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className={cx("status-pop", align === "end" && "end")}
            role="dialog"
            aria-label={t("apps.changeStatus")}
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, transition: { duration: 0.12 } }}
            transition={{ type: "spring", stiffness: 480, damping: 34 }}
          >
            <div className="status-options" role="radiogroup">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  type="button"
                  role="radio"
                  aria-checked={pick === s}
                  className={cx("status-option", pick === s && "on")}
                  style={{ ["--tone" as string]: `var(--st-${s})` }}
                  onClick={() => setPick(s)}
                  onDoubleClick={() => {
                    setPick(s);
                    set.mutate({ id: app.id, status: s, title: app.company || app.role });
                    setOpen(false);
                  }}
                >
                  <span className="status">{t(`status.${s}` as never)}</span>
                </button>
              ))}
            </div>
            <label className="field">
              <span className="label">{t("apps.note")}</span>
              <input
                className="input"
                value={note}
                placeholder={t("apps.notePlaceholder")}
                onChange={(e) => setNote(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && save()}
              />
            </label>
            <div className="status-actions">
              <button type="button" className="btn quiet small" onClick={() => setOpen(false)}>
                {t("apps.cancel")}
              </button>
              <button type="button" className="btn primary small" disabled={pick === app.status && !note} onClick={save}>
                {t("apps.save")}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
