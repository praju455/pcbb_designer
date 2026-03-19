import StatusBadge from "../shared/StatusBadge";

export default function DFMCheckItem({ check }) {
  const status = check.passed ? "ok" : check.severity === "error" ? "error" : "warning";
  return (
    <div className="rounded-[1.5rem] border border-border/70 bg-white/76 p-5 shadow-[0_18px_40px_rgba(15,23,42,0.05)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="font-semibold text-text">{check.name}</div>
        <StatusBadge status={status} label={check.passed ? "pass" : check.severity} />
      </div>
      <div className="grid gap-2 text-sm text-muted md:grid-cols-[1fr_1fr]">
        <div className="rounded-[1rem] bg-background/70 px-3 py-2">
          Found: <span className="text-text">{check.value_found}</span>
        </div>
        <div className="rounded-[1rem] bg-background/70 px-3 py-2">
          Required: <span className="text-text">{check.value_required}</span>
        </div>
      </div>
      <div className="mt-3 rounded-[1rem] bg-white/70 px-3 py-3 text-sm leading-7 text-text">
        {check.recommendation}
      </div>
    </div>
  );
}
