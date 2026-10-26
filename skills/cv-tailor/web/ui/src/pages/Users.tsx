import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Empty, Failed, Loading, PageHead, rowIn } from "../components/Bits";
import { useI18n } from "../i18n";
import type { Key } from "../i18n/en";
import { api } from "../lib/api";
import { ago, cx, shortDate } from "../lib/format";
import { notify } from "../lib/live";
import type { Me, UserRow } from "../lib/types";

const TONE: Record<UserRow["status"], string> = {
  pending: "var(--accent)",
  active: "var(--st-offer)",
  disabled: "var(--ink-3)",
};

export function Users() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const me = qc.getQueryData<Me>(["me"]);
  const q = useQuery({ queryKey: ["users"], queryFn: api.users, enabled: !!me?.is_admin });
  if (!me?.is_admin) return <Navigate to="/" replace />;

  return (
    <div className="users">
      <PageHead title={t("users.title")} lede={t("users.lede")} />
      <p className="muted small users-super">{t("users.superuser", { name: me.user })}</p>
      {q.isLoading ? (
        <Loading rows={4} />
      ) : q.isError ? (
        <Failed q={q} />
      ) : !q.data?.length ? (
        <Empty>{t("users.empty")}</Empty>
      ) : (
        <ul className="user-list">
          <AnimatePresence initial={false}>
            {q.data.map((u, i) => (
              <motion.li key={u.username} layout="position" {...rowIn(i)} className={cx("user-row", u.status)}>
                <UserLine user={u} />
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}

function UserLine({ user }: { user: UserRow }) {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const [pw, setPw] = useState<string | null>(null);
  const done = (rows: UserRow[]) => {
    qc.setQueryData(["users"], rows);
    qc.invalidateQueries({ queryKey: ["me"] });
  };
  const act = useMutation({
    mutationFn: (a: "approve" | "reject" | "disable" | "enable" | "logout-all" | "delete") =>
      a === "delete" ? api.deleteUser(user.username) : api.userAction(user.username, a),
    onSuccess: done,
  });
  const setPassword = useMutation({
    mutationFn: () => api.userPassword(user.username, pw ?? ""),
    onSuccess: (rows) => {
      done(rows);
      setPw(null);
      notify(t("users.passwordSet", { name: user.username }));
    },
  });

  const meta = [
    t("users.created", { date: shortDate(user.created, lang) }),
    user.approved_by && t("users.approvedBy", { name: user.approved_by }),
    user.sessions ? t("users.sessions", { n: user.sessions }) : null,
    user.last_seen && t("users.lastSeen", { ago: ago(user.last_seen, lang) }),
  ].filter(Boolean);

  return (
    <>
      <div className="user-main">
        <p className="user-name">{user.username}</p>
        <p className="user-meta muted small">
          {meta.map((m, i) => (
            <span key={i}>{m}</span>
          ))}
        </p>
      </div>
      <span className="status" style={{ ["--tone" as string]: TONE[user.status] }}>
        {t(`users.status.${user.status}` as Key)}
      </span>
      <div className="user-actions">
        {pw !== null ? (
          <form
            className="user-pw"
            onSubmit={(e) => {
              e.preventDefault();
              if (pw.length >= 8) setPassword.mutate();
            }}
          >
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              autoFocus
              value={pw}
              placeholder={t("users.password")}
              aria-label={t("users.password")}
              onChange={(e) => setPw(e.target.value)}
            />
            <button type="submit" className="btn primary small" disabled={pw.length < 8 || setPassword.isPending}>
              {t("users.save")}
            </button>
            <button type="button" className="btn quiet small" onClick={() => setPw(null)}>
              {t("users.cancel")}
            </button>
          </form>
        ) : user.status === "pending" ? (
          <>
            <button type="button" className="btn accent small" disabled={act.isPending} onClick={() => act.mutate("approve")}>
              {t("users.approve")}
            </button>
            <button type="button" className="btn small" disabled={act.isPending} onClick={() => act.mutate("reject")}>
              {t("users.reject")}
            </button>
          </>
        ) : (
          <>
            {user.status === "active" ? (
              <button type="button" className="btn small" disabled={act.isPending} onClick={() => act.mutate("disable")}>
                {t("users.disable")}
              </button>
            ) : (
              <button type="button" className="btn small" disabled={act.isPending} onClick={() => act.mutate("enable")}>
                {t("users.enable")}
              </button>
            )}
            <button type="button" className="btn quiet small" onClick={() => setPw("")}>
              {t("users.password")}
            </button>
            {user.sessions > 0 && (
              <button type="button" className="btn quiet small" disabled={act.isPending} onClick={() => act.mutate("logout-all")}>
                {t("users.signOutAll")}
              </button>
            )}
            <button
              type="button"
              className="btn quiet small danger"
              disabled={act.isPending}
              onClick={() => window.confirm(t("users.deleteConfirm", { name: user.username })) && act.mutate("delete")}
            >
              {t("users.delete")}
            </button>
          </>
        )}
      </div>
      {(act.isError || setPassword.isError) && (
        <p className="form-error user-error">{((act.error || setPassword.error) as Error).message}</p>
      )}
    </>
  );
}
