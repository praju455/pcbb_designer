import ConfidenceScore from "../verification/ConfidenceScore";
import DFMCheckItem from "./DFMCheckItem";

export default function DFMReport({ report }) {
  if (!report) {
    return (
      <div className="glass rounded-[2rem] p-6">
        <div className="font-serif text-2xl">DFM report</div>
        <div className="mt-4 rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
          No validation report yet. Run a DFM check to see fabrication scoring and issue details here.
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <div className="glass rounded-[2rem] p-6">
        <div className="grid gap-6 md:grid-cols-[220px_1fr]">
          <ConfidenceScore score={Math.round(report.score || 0)} />
          <div>
            <div className="font-serif text-2xl">Gemini assessment</div>
            <p className="mt-3 leading-7 text-muted">{report.ai_summary}</p>
            <div className="mt-4 text-sm text-text">Fabrication success probability: {report.fabrication_success_probability}%</div>
          </div>
        </div>
      </div>
      <div className="grid gap-4">
        {report.checks?.map((check) => <DFMCheckItem key={check.name} check={check} />)}
      </div>
    </div>
  );
}
