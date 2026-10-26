import { motion } from "motion/react";
import { useId } from "react";

export function Segmented<V extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: V;
  options: { value: V; label: string }[];
  onChange: (v: V) => void;
  label: string;
}) {
  const id = useId();
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.value === value && (
            <motion.span
              layoutId={`seg-${id}`}
              className="seg-mark"
              transition={{ type: "spring", stiffness: 520, damping: 40 }}
            />
          )}
          <span style={{ position: "relative" }}>{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export function EffortSwitch({
  value,
  onChange,
  t,
}: {
  value: string;
  onChange: (v: string) => void;
  t: (k: never) => string;
}) {
  const v = value === "medium" ? "medium" : "high";
  return (
    <Segmented
      label={t("effort.label" as never)}
      value={v}
      onChange={onChange}
      options={[
        { value: "high", label: t("effort.high" as never) },
        { value: "medium", label: t("effort.medium" as never) },
      ]}
    />
  );
}
