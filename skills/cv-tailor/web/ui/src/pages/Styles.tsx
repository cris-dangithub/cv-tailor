import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Check, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Failed, Loading, PageHead, rowIn } from "../components/Bits";
import { EffortSwitch } from "../components/Segmented";
import { useI18n } from "../i18n";
import { api } from "../lib/api";
import { cx, shortDate } from "../lib/format";
import { notify } from "../lib/live";
import type { Styles as StylesData } from "../lib/types";

export function Styles() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["styles"], queryFn: api.styles });
  const use = useMutation({
    mutationFn: (name: string) => api.useStyle(name),
    onSuccess: (data: StylesData, name) => {
      qc.setQueryData(["styles"], data);
      qc.invalidateQueries({ queryKey: ["workspace"] });
      notify(t("styles.switched", { name }));
    },
  });
  const since = (name: string) => [...(q.data?.history ?? [])].reverse().find((h) => h.style === name)?.date;

  return (
    <div className="styles-page">
      <PageHead title={t("styles.title")} lede={t("styles.lede")} />
      <div className="styles-body">
        <section>
          {q.isLoading ? (
            <Loading rows={3} />
          ) : q.isError ? (
            <Failed q={q} />
          ) : (
            <ul className="style-list">
              {q.data!.styles.map((s, i) => (
                <motion.li key={`${s.origin}-${s.name}`} className={cx("style-row", s.active && "on")} {...rowIn(i)}>
                  <div className="style-text">
                    <p className="style-name">{s.name}</p>
                    <p className="muted small">
                      {s.origin === "built-in" ? t("styles.builtin") : t("styles.yours")}
                      {s.description && ` · ${s.description}`}
                    </p>
                  </div>
                  <AnimatePresence mode="wait" initial={false}>
                    {s.active ? (
                      <motion.span key="on" className="style-active" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                        <Check size={15} strokeWidth={1.9} aria-hidden />
                        {t("styles.active")}
                        {since(s.name) && <span className="muted small tabular"> · {shortDate(since(s.name), lang)}</span>}
                      </motion.span>
                    ) : (
                      <motion.button key="use" type="button" className="btn small" disabled={use.isPending} onClick={() => use.mutate(s.name)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        {t("styles.use")}
                      </motion.button>
                    )}
                  </AnimatePresence>
                </motion.li>
              ))}
            </ul>
          )}
        </section>
        <NewStyle />
      </div>
    </div>
  );
}

function NewStyle() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [effort, setEffort] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const create = useMutation({
    mutationFn: () => api.styleFromSample(file!, name, effort ?? settings.data?.effort),
    onSuccess: (th) => navigate(`/chat/${th.id}`),
  });
  return (
    <section className="new-style" aria-labelledby="new-style-title">
      <h2 id="new-style-title" className="side-title">
        {t("styles.newTitle")}
      </h2>
      <p className="muted">{t("styles.newLede")}</p>
      <form
        className="new-style-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (file) create.mutate();
        }}
      >
        <div className="field">
          <span className="label">{t("styles.file")}</span>
          <div className="file-pick">
            <button type="button" className="btn small" onClick={() => input.current?.click()}>
              <Upload size={15} strokeWidth={1.6} aria-hidden />
              {t("styles.choose")}
            </button>
            <span className={cx("small", file ? "" : "muted")}>{file?.name ?? t("styles.fileHint")}</span>
            <input ref={input} type="file" hidden accept=".pdf,.docx,.doc,.odt,.html,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
        </div>
        <label className="field">
          <span className="label">{t("styles.name")}</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value.replace(/[^\w-]/g, ""))} />
        </label>
        <div className="feedback-bar">
          <EffortSwitch value={effort ?? settings.data?.effort ?? "high"} onChange={setEffort} t={t as never} />
          <button type="submit" className="btn primary small" disabled={!file || create.isPending}>
            {t("styles.create")}
          </button>
        </div>
        {create.isError && <p className="form-error">{(create.error as Error).message}</p>}
      </form>
    </section>
  );
}
