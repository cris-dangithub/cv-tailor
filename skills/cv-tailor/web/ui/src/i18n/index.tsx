import { createContext, useContext, useMemo, type ReactNode } from "react";
import en, { type Key } from "./en";
import es from "./es";
import id from "./id";

export const LANGUAGES = { en: "English", es: "Español", id: "Bahasa Indonesia" } as const;
export type Lang = keyof typeof LANGUAGES;
const DICTS: Record<Lang, Partial<Record<Key, string>>> = { en, es, id };

type Vars = Record<string, string | number>;
/** "home.generate" for the pair "home.generate_one" / "home.generate_other". */
type PluralKey = Key extends infer K ? (K extends `${infer B}_other` ? B : never) : never;
export type T = (key: Key | PluralKey, vars?: Vars) => string;

interface Ctx {
  lang: Lang;
  t: T;
}

const I18n = createContext<Ctx>({ lang: "en", t: (k) => en[k as Key] ?? k });

export function pickLang(...candidates: (string | null | undefined)[]): Lang {
  for (const c of candidates) {
    const base = (c || "").toLowerCase().split("-")[0];
    if (base in LANGUAGES) return base as Lang;
  }
  return "en";
}

export function I18nProvider({ lang, children }: { lang: Lang; children: ReactNode }) {
  const value = useMemo<Ctx>(() => {
    const dict = DICTS[lang];
    const rules = new Intl.PluralRules(lang);
    const t: T = (key, vars) => {
      let k = key as Key;
      if (vars && typeof vars.n === "number") {
        const plural = `${key}_${rules.select(vars.n)}` as Key;
        const other = `${key}_other` as Key;
        k = (plural in en ? plural : other in en ? other : key) as Key;
      }
      let s = dict[k] ?? en[k] ?? String(k);
      if (vars) for (const [name, v] of Object.entries(vars)) s = s.replaceAll(`{${name}}`, String(v));
      return s;
    };
    return { lang, t };
  }, [lang]);
  return <I18n.Provider value={value}>{children}</I18n.Provider>;
}

export const useI18n = () => useContext(I18n);
