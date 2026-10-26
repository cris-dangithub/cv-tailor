import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api, ApiError } from "../lib/api";
import { cx } from "../lib/format";

type Mode = "signIn" | "register";

export function Login() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>("signIn");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const go = useMutation({
    mutationFn: () => (mode === "signIn" ? api.login(username, password) : api.register(username, password)),
    onSuccess: (data) => {
      if ("status" in data) {
        setNotice(t("auth.pendingCreated"));
        setMode("signIn");
        setPassword("");
        return;
      }
      // signing out reloads the page, so nothing of a previous user is left in the cache
      qc.setQueryData(["me"], data);
    },
  });

  const err = go.error as ApiError | null;
  const errorText = err
    ? ((): string => {
        const key = `auth.err.${err.message}` as Key;
        const known = t(key);
        return known !== key ? known.replace("{s}", String(err.retryAfter || 60)) : t("auth.err.generic", { msg: err.message });
      })()
    : null;

  return (
    <div className="login">
      <section className="login-side" aria-hidden>
        <p className="login-mark">
          <span className="wordmark-cv">cv</span>
          <span className="wordmark-tailor">tailor</span>
        </p>
      </section>
      <motion.section
        className="login-main"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <h1 className="display login-title">{t("auth.headline")}</h1>
        <LayoutGroup id="login-mode">
          <div className="filter-tabs login-tabs" role="tablist">
            {(["signIn", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                className={cx("filter-tab", mode === m && "on")}
                onClick={() => {
                  setMode(m);
                  go.reset();
                  setNotice(null);
                }}
              >
                <span>{t(m === "signIn" ? "auth.signIn" : "auth.register")}</span>
                {mode === m && <motion.span layoutId="login-mark" className="filter-mark" transition={{ type: "spring", stiffness: 500, damping: 40 }} />}
              </button>
            ))}
          </div>
        </LayoutGroup>
        <AnimatePresence mode="wait" initial={false}>
          <motion.p
            key={mode}
            className="muted login-lede"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }}
          >
            {mode === "signIn" ? t("auth.lede") : t("auth.registerLede")}
          </motion.p>
        </AnimatePresence>
        <form
          className="login-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (username && password) go.mutate();
          }}
        >
          <label className="field">
            <span className="label">{t("auth.username")}</span>
            <input
              className="input"
              value={username}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              autoFocus
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="label">{t("auth.password")}</span>
            <input
              className="input"
              type="password"
              value={password}
              autoComplete={mode === "signIn" ? "current-password" : "new-password"}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <AnimatePresence>
            {(errorText || notice) && (
              <motion.p
                key={errorText || notice}
                className={cx("login-message", errorText ? "error" : "ok")}
                role={errorText ? "alert" : "status"}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                {errorText || notice}
              </motion.p>
            )}
          </AnimatePresence>
          <button type="submit" className="btn primary login-submit" disabled={!username || !password || go.isPending}>
            {t(mode === "signIn" ? "auth.signIn" : "auth.register")}
            <ArrowRight size={16} strokeWidth={1.7} aria-hidden />
          </button>
        </form>
      </motion.section>
    </div>
  );
}
