import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { LogOut, Moon, Sun, SunMoon } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, useLocation, useOutlet } from "react-router-dom";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api } from "../lib/api";
import { cx } from "../lib/format";
import type { Me } from "../lib/types";
import { useConnected, useNotices } from "../lib/live";
import { applyTheme, storedTheme, type Theme } from "../lib/theme";

const NAV: { to: string; key: Key; mobile: boolean }[] = [
  { to: "/", key: "nav.desk", mobile: true },
  { to: "/applications", key: "nav.applications", mobile: true },
  { to: "/documents", key: "nav.documents", mobile: true },
  { to: "/chat", key: "nav.chat", mobile: true },
  { to: "/styles", key: "nav.styles", mobile: false },
  { to: "/settings", key: "nav.settings", mobile: true },
  { to: "/users", key: "nav.users", mobile: false },
];

function section(path: string) {
  const first = path.split("/")[1] || "desk";
  // a conversation and its list are one screen on wide displays: no page change between them
  return first === "chat" && window.matchMedia("(min-width: 960px)").matches ? "chat" : path;
}

export function Shell() {
  const { t } = useI18n();
  const location = useLocation();
  const outlet = useOutlet();
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const threads = useQuery({ queryKey: ["threads"], queryFn: api.threads });
  const online = useConnected();
  const me = useQuery<Me>({ queryKey: ["me"], queryFn: api.me, staleTime: 60_000 });
  const nav = NAV.filter((n) => n.to !== "/users" || me.data?.is_admin);
  const needsYou = (threads.data ?? []).filter((x) => x.status === "waiting" || (x.unread && x.status !== "running")).length;
  const working = (threads.data ?? []).some((x) => x.status === "running");

  const badge = (to: string) => {
    if (to === "/applications" && ws.data) return <span className="nav-count tabular">{ws.data.total}</span>;
    if (to === "/chat" && needsYou) return <span className="nav-dot" aria-label={String(needsYou)} />;
    if (to === "/chat" && working) return <span className="nav-pulse" aria-hidden />;
    if (to === "/users" && me.data?.pending_users) return <span className="nav-dot" aria-label={String(me.data.pending_users)} />;
    return null;
  };

  return (
    <div className="shell">
      <a href="#main" className="skip">
        {t("common.skip")}
      </a>
      <aside className="rail">
        <Link to="/" className="wordmark" aria-label="cv-tailor">
          <span className="wordmark-cv">cv</span>
          <span className="wordmark-tailor">tailor</span>
        </Link>
        <nav className="rail-nav" aria-label="Main">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className="rail-link">
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="rail-mark"
                      className="rail-mark"
                      transition={{ type: "spring", stiffness: 520, damping: 42 }}
                    />
                  )}
                  <span className="rail-label">{t(n.key)}</span>
                  {badge(n.to)}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="rail-foot">
          <p className="rail-who">
            <span className="rail-name">{me.data?.user}</span>
            {ws.data && (
              <span className="muted small" title={ws.data.path}>
                {ws.data.candidate || ws.data.name}
              </span>
            )}
          </p>
          <div className="rail-tools">
            <ThemeToggle />
            <SignOut />
          </div>
        </div>
      </aside>

      <main id="main" className="stage">
        <SignInNotice />
        {me.data?.default_admin_password && <p className="signin admin-default" role="alert">{t("auth.defaultPassword")}</p>}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={section(location.pathname)}
            className="page"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.16, 1, 0.3, 1] } }}
            exit={{ opacity: 0, transition: { duration: 0.12 } }}
          >
            {outlet}
          </motion.div>
        </AnimatePresence>
      </main>

      <nav className="tabbar" aria-label="Main">
        {NAV.filter((n) => n.mobile).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"} className="tab">
            {({ isActive }) => (
              <>
                {isActive && <motion.span layoutId="tab-mark" className="tab-mark" transition={{ type: "spring", stiffness: 520, damping: 42 }} />}
                <span>{t(n.key === "nav.chat" ? "nav.chatShort" : n.key)}</span>
                {n.to === "/chat" && needsYou > 0 && <span className="nav-dot" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <Ticker />
      <AnimatePresence>
        {!online && (
          <motion.p
            className="offline"
            role="status"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            {t("common.reconnecting")}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

function SignInNotice() {
  const { t } = useI18n();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 60_000 });
  const [copied, setCopied] = useState(false);
  return (
    <AnimatePresence>
      {health.data?.logged_in === false && (
        <motion.aside
          className="signin"
          role="alert"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <p>{t("health.loggedOut")}</p>
          <div className="signin-row">
            <button
              type="button"
              className="signin-cmd mono"
              title="Copy"
              onClick={() => {
                navigator.clipboard?.writeText("claude auth login").then(() => setCopied(true));
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              claude auth login
              <span className="muted small">{copied ? "✓" : ""}</span>
            </button>
            <button type="button" className="btn small" disabled={health.isFetching} onClick={() => health.refetch()}>
              {t("health.recheck")}
            </button>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

export function SignOut({ withLabel = false }: { withLabel?: boolean }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  return (
    <button
      type="button"
      className={cx("btn quiet small", !withLabel && "icon")}
      aria-label={t("auth.signOut")}
      title={t("auth.signOut")}
      onClick={async () => {
        await api.logout().catch(() => {});
        qc.clear();
        window.location.assign("/");
      }}
    >
      <LogOut size={16} strokeWidth={1.6} aria-hidden />
      {withLabel && t("auth.signOut")}
    </button>
  );
}

function ThemeToggle() {
  const { t } = useI18n();
  const [theme, setTheme] = useState<Theme>(storedTheme());
  const next: Record<Theme, Theme> = { auto: "light", light: "dark", dark: "auto" };
  const Icon = theme === "auto" ? SunMoon : theme === "light" ? Sun : Moon;
  return (
    <button
      type="button"
      className="btn quiet small icon"
      aria-label={`${t("settings.theme")}: ${t(`theme.${theme}` as Key)}`}
      title={`${t("settings.theme")}: ${t(`theme.${theme}` as Key)}`}
      onClick={() => {
        const n = next[theme];
        setTheme(n);
        applyTheme(n);
      }}
    >
      <Icon size={16} strokeWidth={1.6} />
    </button>
  );
}

function Ticker() {
  const notices = useNotices();
  return (
    <div className="ticker" aria-live="polite">
      <AnimatePresence initial={false}>
        {notices.map((n) => (
          <motion.div
            key={n.id}
            layout
            className="ticker-item"
            initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, x: -12, transition: { duration: 0.18 } }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
          >
            {n.href ? (
              <Link to={n.href} className={cx("ticker-link")}>
                {n.text}
              </Link>
            ) : (
              n.text
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
