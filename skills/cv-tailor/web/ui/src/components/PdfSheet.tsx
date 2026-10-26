// A PDF drawn as paper sheets on the table (pdf.js), so it looks the same on a phone, where
// browsers often refuse to show PDFs inline.
import { motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

type PdfJs = typeof import("pdfjs-dist");
let pdfjsPromise: Promise<PdfJs> | null = null;

function loadPdfJs() {
  pdfjsPromise ??= Promise.all([import("pdfjs-dist"), import("pdfjs-dist/build/pdf.worker.min.mjs?url")]).then(
    ([lib, worker]) => {
      lib.GlobalWorkerOptions.workerSrc = worker.default;
      return lib;
    },
  );
  return pdfjsPromise;
}

export function PdfSheet({ url, label }: { url: string; label: string }) {
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
        const t = lib.getDocument({ url });
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
    const paint = async () => {
      const width = el.clientWidth;
      if (!width || Math.abs(width - lastWidth) < 24) return;
      lastWidth = width;
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      for (let i = 1; i <= pdf.numPages && !cancelled; i++) {
        const canvas = el.querySelector<HTMLCanvasElement>(`canvas[data-page="${i}"]`);
        if (!canvas) continue;
        const page = await pdf.getPage(i);
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: (width / base.width) * dpr });
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.aspectRatio = `${base.width} / ${base.height}`;
        await page.render({ canvas, canvasContext: canvas.getContext("2d")!, viewport }).promise.catch(() => {});
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
        <object data={url} type="application/pdf" className="pdf-fallback" aria-label={label}>
          <a className="link" href={url} target="_blank" rel="noreferrer">
            {label}
          </a>
        </object>
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
