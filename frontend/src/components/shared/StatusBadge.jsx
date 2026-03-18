const styles = {
  ok: "bg-success/15 text-success border-success/30",
  error: "bg-error/12 text-error border-error/30",
  warning: "bg-warning/15 text-warning border-warning/30",
  idle: "bg-white/60 text-text border-border/60"
};

export default function StatusBadge({ status = "idle", label }) {
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${styles[status] || styles.idle}`}>{label}</span>;
}
