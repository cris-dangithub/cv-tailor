export type Theme = "auto" | "light" | "dark";
const KEY = "cvt-theme";

export function storedTheme(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "auto";
  } catch {
    return "auto";
  }
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
  try {
    if (theme === "auto") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, theme);
  } catch {
    /* private mode */
  }
}

export function remember<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(`cvt-${key}`) as T) || fallback;
  } catch {
    return fallback;
  }
}

export function keep(key: string, value: string) {
  try {
    localStorage.setItem(`cvt-${key}`, value);
  } catch {
    /* private mode */
  }
}
