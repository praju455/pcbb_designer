import StatusBadge from "../shared/StatusBadge";

export default function DFMCheckItem({ check }) {
  const status = check.passed ? "ok" : check.severity === "error" ? "error" : "warning";
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-semibold">{check.name}</div>
        <StatusBadge status={status} label={check.passed ? "pass" : check.severity} />
      </div>
      <div className="text-sm text-muted">{check.value_found} vs {check.value_required}</div>
      <div className="mt-2 text-sm">{check.recommendation}</div>
    </div>
  );
}
