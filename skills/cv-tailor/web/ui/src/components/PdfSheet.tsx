// A PDF drawn as paper sheets on the table (pdf.js), so it looks the same on a phone, where
// browsers often refuse to show PDFs inline. The legacy build of pdf.js 4 is the one that runs
// on iPhone browsers (all of them are Safari's WebKit underneath).
import { motion } from "motion/react";
import { Download, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { useI18n } from "../i18n";

type PdfJs = typeof import("pdfjs-dist");
let pdfjsPromise: Promise<PdfJs> | null = null;

function loadPdfJs() {
  pdfjsPromise ??= Promise.all([
    import("pdfjs-dist/legacy/build/pdf.mjs") as Promise<PdfJs>,
    import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?url"),
  ]).then(([lib, worker]) => {
    lib.GlobalWorkerOptions.workerSrc = worker.default;
    return lib;
  });
  pdfjsPromise.catch(() => (pdfjsPromise = null)); // a failed load may succeed on the next try
  return pdfjsPromise;
}

const withDownload = (url: string) => `${url}${url.includes("?") ? "&" : "?"}download=1`;

export function PdfSheet({ url, label }: { url: string; label: string }) {
  const { t } = useI18n();
  const host = useRef<HTMLDivElement>(null);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [failed, setFailed] = useState(false);

  // 1. load the document
  useEffect(() => {
    let cancelled = false;
    let task: { destroy: () => Promise<void> } | null = null;
    setPdf(null);
    setFailed(false);
    loadPdfJs()
      .then((lib) => {
        const t = lib.getDocument({ url, isEvalSupported: false });
        task = t;
        return t.promise;
      })
      .then((doc) => !cancelled && setPdf(doc))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      task?.destroy();
    };
  }, [url]);

  // 2. paint its pages once their canvases exist, and again when the column changes width
  useEffect(() => {
    const el = host.current;
    if (!pdf || !el) return;
    let cancelled = false;
    let lastWidth = 0;
    let queue = Promise.resolve();
    // one paint at a time: pdf.js refuses two renders on the same canvas
    const paint = () => {
      queue = queue.then(paintNow);
    };
    const paintNow = async () => {
      const width = el.clientWidth;
      if (!width || Math.abs(width - lastWidth) < 24) return;
      lastWidth = width;
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      try {
        for (let i = 1; i <= pdf.numPages && !cancelled; i++) {
          const canvas = el.querySelector<HTMLCanvasElement>(`canvas[data-page="${i}"]`);
          if (!canvas) continue;
          const page = await pdf.getPage(i);
          const base = page.getViewport({ scale: 1 });
          const viewport = page.getViewport({ scale: (width / base.width) * dpr });
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          canvas.style.aspectRatio = `${base.width} / ${base.height}`;
          await page.render({ canvasContext: canvas.getContext("2d")!, viewport }).promise;
        }
      } catch {
        if (!cancelled) setFailed(true); // this browser cannot draw it: offer to open it instead
      }
    };
    paint();
    const ro = new ResizeObserver(() => paint());
    ro.observe(el);
    return () => {
      cancelled = true;
      ro.disconnect();
    };
  }, [pdf]);

  return (
    <div className="pdf-sheets" ref={host} aria-label={label}>
      {failed ? (
        <div className="sheet pdf-fallback" role="note">
          <p>{t("pdf.cantShow")}</p>
          <div className="pdf-fallback-actions">
            <a className="btn primary small" href={url} target="_blank" rel="noreferrer">
              <ExternalLink size={15} strokeWidth={1.6} aria-hidden />
              {t("pdf.open")}
            </a>
            <a className="btn small" href={withDownload(url)} download>
              <Download size={15} strokeWidth={1.6} aria-hidden />
              {t("detail.download")}
            </a>
          </div>
        </div>
      ) : !pdf ? (
        <div className="sheet sheet-placeholder skeleton" />
      ) : (
        Array.from({ length: pdf.numPages }, (_, i) => (
          <motion.div
            key={`${url}-${i}`}
            className="sheet"
            initial={{ opacity: 0, y: 16, rotate: i % 2 ? 0.35 : -0.35 }}
            animate={{ opacity: 1, y: 0, rotate: 0 }}
            transition={{ type: "spring", stiffness: 110, damping: 20, delay: i * 0.07 }}
          >
            <canvas data-page={i + 1} />
          </motion.div>
        ))
      )}
    </div>
  );
}
