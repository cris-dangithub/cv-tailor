import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Failed, Loading, PageHead } from "../components/Bits";
import { Segmented } from "../components/Segmented";
import { LANGUAGES, useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api } from "../lib/api";
import { applyTheme, storedTheme, type Theme } from "../lib/theme";
import type { Settings as SettingsData } from "../lib/types";

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="set-row">
      <div className="set-label">
        <p className="set-name">{label}</p>
        {hint && <p className="muted small">{hint}</p>}
      </div>
      <div className="set-control">{children}</div>
    </div>
  );
}

export function Settings() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const [saved, setSaved] = useState(false);
  const [theme, setTheme] = useState<Theme>(storedTheme());
  const [model, setModel] = useState("");
  useEffect(() => setModel(q.data?.model ?? ""), [q.data?.model]);

  const save = useMutation({
    mutationFn: (s: Partial<SettingsData>) => api.saveSettings(s),
    onSuccess: (data) => {
      qc.setQueryData(["settings"], data);
      setSaved(true);
      setTimeout(() => setSaved(false), 1600);
    },
  });

  if (q.isLoading) return <Loading rows={6} />;
  if (q.isError || !q.data) return <Failed q={q} />;
  const s = q.data;

  return (
    <div className="settings">
      <PageHead
        title={t("settings.title")}
        aside={
          <AnimatePresence>
            {saved && (
              <motion.span className="saved" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                {t("settings.saved")}
              </motion.span>
            )}
          </AnimatePresence>
        }
      />

      <Link to="/styles" className="settings-styles-link link">
        {t("nav.styles")}
        <ArrowRight size={14} strokeWidth={1.7} aria-hidden />
      </Link>

      <section className="set-section">
        <h2 className="side-title">{t("settings.agent")}</h2>
        <Row label={t("settings.model")} hint={t("settings.modelHint")}>
          <input
            className="input mono"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            onBlur={() => model.trim() && model !== s.model && save.mutate({ model: model.trim() })}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          />
        </Row>
        <Row label={t("settings.effort")} hint={t("settings.effortHint")}>
          <Segmented
            label={t("settings.effort")}
            value={s.effort === "medium" ? "medium" : "high"}
            onChange={(v) => save.mutate({ effort: v })}
            options={[
              { value: "high", label: t("effort.high") },
              { value: "medium", label: t("effort.medium") },
            ]}
          />
        </Row>
        <Row label={t("settings.autocompact")} hint={t("settings.autocompactHint")}>
          <select className="select compact" value={s.autocompact} onChange={(e) => save.mutate({ autocompact: e.target.value })}>
            {["100k", "150k", "200k", "400k", "auto"].map((v) => (
              <option key={v} value={v}>
                {v === "auto" ? "auto" : `${v} tokens`}
              </option>
            ))}
          </select>
        </Row>
        <Row label={t("settings.concurrency")} hint={t("settings.concurrencyHint")}>
          <Segmented
            label={t("settings.concurrency")}
            value={String(s.concurrency)}
            onChange={(v) => save.mutate({ concurrency: Number(v) })}
            options={["1", "2", "3", "4"].map((n) => ({ value: n, label: n }))}
          />
        </Row>
      </section>

      <section className="set-section">
        <h2 className="side-title">{t("settings.interface")}</h2>
        <Row label={t("settings.language")}>
          <select className="select compact" value={s.ui_language ?? ""} onChange={(e) => save.mutate({ ui_language: e.target.value || null })}>
            <option value="">{t("settings.languageAuto")}{ws.data ? ` (${ws.data.ui_language})` : ""}</option>
            {Object.entries(LANGUAGES).map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </Row>
        <Row label={t("settings.theme")}>
          <Segmented<Theme>
            label={t("settings.theme")}
            value={theme}
            onChange={(v) => {
              setTheme(v);
              applyTheme(v);
            }}
            options={(["auto", "light", "dark"] as Theme[]).map((v) => ({ value: v, label: t(`theme.${v}` as Key) }))}
          />
        </Row>
      </section>

      <section className="set-section">
        <h2 className="side-title">{t("settings.lan")}</h2>
        {!ws.data?.lan ? (
          <p className="muted set-copy">{t("settings.lanRemote")}</p>
        ) : !ws.data.lan.enabled ? (
          <p className="muted set-copy">{t("settings.lanOff")}</p>
        ) : (
          <div className="lan">
            <p className="muted set-copy">{t("settings.lanOn")}</p>
            <img className="lan-qr" src="/api/lan/qr.svg" alt="QR" width={168} height={168} />
            <ul className="lan-urls">
              {ws.data.lan.urls.map((u) => (
                <li key={u} className="mono">
                  {u}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="set-section">
        <h2 className="side-title">{t("settings.permissions")}</h2>
        {s.always_allow.length === 0 ? (
          <p className="muted set-copy">{t("settings.permissionsNone")}</p>
        ) : (
          <ul className="rules">
            {s.always_allow.map((r) => (
              <li key={r}>
                <span className="mono">{r}</span>
                <button
                  type="button"
                  className="btn quiet small icon"
                  aria-label={`${t("settings.remove")} ${r}`}
                  onClick={() => save.mutate({ always_allow: s.always_allow.filter((x) => x !== r) })}
                >
                  <X size={15} strokeWidth={1.6} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {ws.data && (
        <section className="set-section">
          <h2 className="side-title">{t("settings.workspace")}</h2>
          <Row label={t("settings.candidate")}>
            <span>{ws.data.candidate || "—"}</span>
          </Row>
          <Row label={t("settings.workspace")}>
            <span className="mono small set-path">{ws.data.path}</span>
          </Row>
        </section>
      )}
    </div>
  );
}
