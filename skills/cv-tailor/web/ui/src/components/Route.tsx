// The signature of the app: an application's journey drawn as one fine line through the
// stations it can reach. A closed application (rejected / withdrawn) ends in a cut mark where
// it stopped.
import { motion } from "motion/react";
import { useI18n } from "../i18n";
import { shortDate, cx } from "../lib/format";
import type { Status, StatusEntry } from "../lib/types";

const PATH: Status[] = ["generated", "sent", "replied", "interview", "offer"];
const ENDS: Status[] = ["rejected", "withdrawn"];

export function reached(status: Status, history: StatusEntry[] = []): number {
  let best = 0;
  for (const h of [...history, { status }]) {
    const i = PATH.indexOf(h.status as Status);
    if (i > best) best = i;
  }
  return best;
}

function dateOf(s: Status, history: StatusEntry[]) {
  for (let i = history.length - 1; i >= 0; i--) if (history[i].status === s) return history[i].date;
  return "";
}

export function Route({
  status,
  history = [],
  size = "small",
}: {
  status: Status;
  history?: StatusEntry[];
  size?: "small" | "large";
}) {
  const { t, lang } = useI18n();
  const at = reached(status, history);
  const ended = ENDS.includes(status);
  const frac = at / (PATH.length - 1);
  const spring = { type: "spring", stiffness: 140, damping: 26 } as const;

  return (
    <div
      className={cx("route", `route-${size}`, ended && "route-ended")}
      style={{ ["--tone" as string]: `var(--st-${status})` }}
      role="img"
      aria-label={`${t(`status.${status}` as never)}`}
    >
      <div className="route-track">
        <motion.div
          className="route-progress"
          initial={false}
          animate={{ scaleX: frac }}
          transition={spring}
        />
        {PATH.map((s, i) => {
          const done = i <= at;
          const current = i === at;
          return (
            <div key={s} className="route-station" style={{ left: `${(i / (PATH.length - 1)) * 100}%` }}>
              <motion.span
                className={cx("route-dot", done && "done", current && "current")}
                initial={false}
                animate={{ scale: current ? 1 : done ? 0.78 : 0.62 }}
                transition={{ ...spring, delay: done ? i * 0.04 : 0 }}
              />
              {size === "large" && (
                <span className={cx("route-label", done && "done")}>
                  <span>{t(`status.${s}` as never)}</span>
                  <span className="route-date tabular">{done ? shortDate(dateOf(s, history), lang) : ""}</span>
                </span>
              )}
            </div>
          );
        })}
        {ended && (
          <motion.span
            className="route-cut"
            style={{ left: `${frac * 100}%` }}
            initial={{ opacity: 0, rotate: 0 }}
            animate={{ opacity: 1, rotate: 28 }}
            transition={spring}
          />
        )}
      </div>
      {size === "large" && ended && (
        <p className="route-end-note">
          <span className="status">{t(`status.${status}` as never)}</span>
          <span className="muted small tabular">{shortDate(dateOf(status, history), lang)}</span>
        </p>
      )}
    </div>
  );
}
