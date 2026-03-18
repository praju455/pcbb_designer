import StatusBadge from "../shared/StatusBadge";

export default function StatusCard({ title, value, subtitle, status = "idle" }) {
  return (
    <div className="glass rounded-3xl p-5 transition duration-200 hover:-translate-y-1 hover:shadow-glow">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm text-muted">{title}</div>
        <StatusBadge status={status} label={status} />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="mt-2 text-sm text-muted">{subtitle}</div>
    </div>
  );
}
