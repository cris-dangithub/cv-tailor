/** "000014" -> "014": the number reads as a folio, never as a long zero run. */
export function folio(id: string | number | null | undefined): string {
  const n = String(id ?? "").replace(/^0+(?=\d)/, "");
  return n.padStart(3, "0");
}

export function shortDate(iso: string | undefined | null, lang: string): string {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  if (Number.isNaN(d.getTime())) return iso;
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return new Intl.DateTimeFormat(lang, sameYear ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" }).format(d);
}

export function ago(iso: string | undefined | null, lang: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const s = (d.getTime() - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto", style: "short" });
  const abs = Math.abs(s);
  if (abs < 45) return rtf.format(Math.round(s), "second");
  if (abs < 3600) return rtf.format(Math.round(s / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(s / 3600), "hour");
  if (abs < 86400 * 7) return rtf.format(Math.round(s / 86400), "day");
  return shortDate(iso, lang);
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function langName(code: string | null | undefined, ui: string): string {
  if (!code) return "";
  try {
    const n = new Intl.DisplayNames([ui], { type: "language" }).of(code);
    return n ? n.charAt(0).toUpperCase() + n.slice(1) : code.toUpperCase();
  } catch {
    return code.toUpperCase();
  }
}

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
