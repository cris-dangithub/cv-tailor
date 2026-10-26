import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Download, Eye, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Empty, Failed, Loading, PageHead, rowIn, StatusWord } from "../components/Bits";
import { PdfSheet } from "../components/PdfSheet";
import { Segmented } from "../components/Segmented";
import { useI18n } from "../i18n";
import { api, fileUrl, saveBlob } from "../lib/api";
import { bytes, cx, folio, shortDate } from "../lib/format";
import type { PdfRow } from "../lib/types";
import { PdfFacts } from "./ApplicationDetail";

const keyOf = (p: PdfRow) => `${p.app_id}/${p.name}`;

export function Documents() {
  const { t, lang } = useI18n();
  const q = useQuery({ queryKey: ["pdfs"], queryFn: api.pdfs });
  const [langPick, setLangPick] = useState("all");
  const [onlyCurrent, setOnlyCurrent] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<PdfRow | null>(null);

  const all = useMemo(() => q.data ?? [], [q.data]);
  const langs = useMemo(() => [...new Set(all.map((p) => p.lang).filter(Boolean))] as string[], [all]);
  const groups = useMemo(() => {
    // "current" = the PDF meta.json points at; applications without that mark keep every PDF
    const hasCurrent = new Set(all.filter((p) => p.current).map((p) => `${p.app_id}:${p.lang}`));
    const rows = all.filter(
      (p) => (langPick === "all" || p.lang === langPick) && (!onlyCurrent || p.current || !hasCurrent.has(`${p.app_id}:${p.lang}`)),
    );
    const m = new Map<string, PdfRow[]>();
    rows.forEach((p) => m.set(p.app_id, [...(m.get(p.app_id) ?? []), p]));
    return [...m.values()];
  }, [all, langPick, onlyCurrent]);

  const zip = useMutation({
    mutationFn: () => api.zip(all.filter((p) => selected.has(keyOf(p))).map((p) => ({ app_id: p.app_id, name: p.name }))),
    onSuccess: ({ blob, name }) => saveBlob(blob, name),
  });

  const toggle = (k: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setPreview(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="documents">
      <PageHead title={t("docs.title")} lede={t("docs.lede")} />

      <div className="docs-tools">
        {langs.length > 1 && (
          <Segmented
            label={t("docs.title")}
            value={langPick}
            onChange={setLangPick}
            options={[{ value: "all", label: t("docs.allLangs") }, ...langs.map((l) => ({ value: l, label: l.toUpperCase() }))]}
          />
        )}
        <label className="check">
          <input type="checkbox" checked={onlyCurrent} onChange={(e) => setOnlyCurrent(e.target.checked)} />
          {t("docs.onlyCurrent")}
        </label>
      </div>

      {q.isLoading ? (
        <Loading rows={6} />
      ) : q.isError ? (
        <Failed q={q} />
      ) : !groups.length ? (
        <Empty>{t("docs.empty")}</Empty>
      ) : (
        <div className="doc-groups">
          {groups.map((g, gi) => (
            <motion.section key={g[0].app_id} className="doc-group" {...rowIn(gi)}>
              <header className="doc-group-head">
                <span className="num doc-group-num">{folio(g[0].app_id)}</span>
                <Link to={`/applications/${g[0].app_id}`} className="doc-group-title">
                  <span className="doc-company">{g[0].company || "—"}</span>
                  <span className="muted">{g[0].role}</span>
                </Link>
                <StatusWord status={g[0].status} />
              </header>
              <ul className="doc-rows">
                {g.map((p) => {
                  const k = keyOf(p);
                  return (
                    <li key={k} className={cx("doc-row", selected.has(k) && "picked")}>
                      <label className="doc-check">
                        <input type="checkbox" checked={selected.has(k)} onChange={() => toggle(k)} aria-label={t("docs.select", { name: p.name })} />
                      </label>
                      <button type="button" className="doc-name" onClick={() => setPreview(p)}>
                        <span className="doc-lang">{(p.lang ?? "?").toUpperCase()}</span>
                        <span className="doc-file">{p.name}</span>
                        {p.version > 1 && <span className="doc-v tabular">v{p.version}</span>}
                      </button>
                      <span className="doc-facts muted small tabular">
                        {p.pages ? t("detail.pages", { n: p.pages }) : ""}
                        {p.fits === false && <span className="warn"> · {t("detail.overflows")}</span>}
                      </span>
                      <span className="muted small tabular doc-size">{bytes(p.size)}</span>
                      <span className="muted small tabular doc-date">{shortDate(new Date(p.modified * 1000).toISOString(), lang)}</span>
                      <span className="doc-actions">
                        <button type="button" className="btn quiet small icon" aria-label={t("docs.preview")} title={t("docs.preview")} onClick={() => setPreview(p)}>
                          <Eye size={16} strokeWidth={1.6} />
                        </button>
                        <a className="btn quiet small icon" aria-label={t("detail.download")} title={t("detail.download")} href={fileUrl(p.app_id, p.name, true)} download>
                          <Download size={16} strokeWidth={1.6} />
                        </a>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </motion.section>
          ))}
        </div>
      )}

      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            className="selection-bar"
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0, transition: { duration: 0.16 } }}
            transition={{ type: "spring", stiffness: 380, damping: 34 }}
          >
            <span className="tabular">{t("docs.selected", { n: selected.size })}</span>
            <button type="button" className="btn quiet small" onClick={() => setSelected(new Set())}>
              {t("docs.clear")}
            </button>
            <button type="button" className="btn accent small" disabled={zip.isPending} onClick={() => zip.mutate()}>
              <Download size={15} strokeWidth={1.7} aria-hidden />
              {t("docs.zip")}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {preview && (
          <>
            <motion.div className="scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setPreview(null)} />
            <motion.aside
              className="drawer"
              role="dialog"
              aria-modal="true"
              aria-label={preview.name}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%", transition: { duration: 0.2, ease: [0.5, 0, 0.75, 0] } }}
              transition={{ type: "spring", stiffness: 260, damping: 32 }}
            >
              <header className="drawer-head">
                <div className="drawer-heading">
                  <p className="drawer-title">
                    <span className="num">{folio(preview.app_id)}</span> {preview.company}
                  </p>
                  <p className="muted small">{preview.name}</p>
                </div>
                <div className="drawer-actions">
                  <a className="btn small" href={fileUrl(preview.app_id, preview.name, true)} download>
                    <Download size={15} strokeWidth={1.6} aria-hidden />
                    {t("detail.download")}
                  </a>
                  <button type="button" className="btn quiet small icon" aria-label={t("docs.close")} onClick={() => setPreview(null)} autoFocus>
                    <X size={17} strokeWidth={1.6} />
                  </button>
                </div>
              </header>
              <PdfFacts pdf={preview} />
              <PdfSheet url={fileUrl(preview.app_id, preview.name)} label={preview.name} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
