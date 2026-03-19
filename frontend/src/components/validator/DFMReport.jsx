import ConfidenceScore from "../verification/ConfidenceScore";
import DFMCheckItem from "./DFMCheckItem";

function sanitizeSummary(value) {
  if (!value) {
    return "Run a validation pass to get a concise fabrication assessment.";
  }
  return value
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 420);
}

function summarizeChecks(checks = []) {
  const errors = checks.filter((check) => !check.passed && check.severity === "error").length;
  const warnings = checks.filter((check) => !check.passed && check.severity !== "error").length;
  const passed = checks.filter((check) => check.passed).length;
  return { errors, warnings, passed };
}

export default function DFMReport({ report }) {
  if (!report) {
    return (
      <div className="glass rounded-[2rem] p-6">
        <div className="font-serif text-2xl">DFM report</div>
        <div className="mt-4 rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm leading-7 text-muted">
          No validation report yet. Run a DFM check to see a clean fabrication summary and issue list here.
        </div>
      </div>
    );
  }

  const summary = sanitizeSummary(report.ai_summary);
  const stats = summarizeChecks(report.checks);
  const topFixes = Array.from(new Set((report.suggested_fixes || []).filter(Boolean))).slice(0, 3);

  return (
    <div className="space-y-6">
      <div className="glass rounded-[2rem] p-6">
        <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
          <ConfidenceScore score={Math.round(report.score || 0)} label={report.passed ? "Fabrication ready" : "Needs review"} />
          <div className="space-y-5">
            <div className="flex flex-wrap gap-3 text-sm">
              <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-emerald-700">
                {stats.passed} passed
              </div>
              <div className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-amber-700">
                {stats.warnings} warnings
              </div>
              <div className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-rose-700">
                {stats.errors} errors
              </div>
              <div className="rounded-full border border-border/70 bg-white/70 px-3 py-1.5 text-text">
                {report.fabrication_success_probability}% success estimate
              </div>
            </div>

            <div>
              <div className="font-serif text-2xl">Fabrication assessment</div>
              <p className="mt-3 max-w-3xl leading-7 text-muted">{summary}</p>
            </div>

            {topFixes.length > 0 && (
              <div>
                <div className="text-sm font-semibold uppercase tracking-[0.2em] text-muted">Priority fixes</div>
                <div className="mt-3 flex flex-wrap gap-3">
                  {topFixes.map((fix) => (
                    <div key={fix} className="rounded-[1.2rem] border border-border/70 bg-white/75 px-4 py-3 text-sm leading-6 text-text shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
                      {fix}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4">
        {report.checks?.map((check) => (
          <DFMCheckItem key={check.name} check={check} />
        ))}
      </div>
    </div>
  );
}
