const styles = {
  ok: "bg-success/20 text-success border-success/40",
  error: "bg-error/20 text-error border-error/40",
  warning: "bg-warning/20 text-warning border-warning/40",
  idle: "bg-white/10 text-text border-white/10"
};

export default function StatusBadge({ status = "idle", label }) {
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${styles[status] || styles.idle}`}>{label}</span>;
}
