import ConfidenceScore from "../verification/ConfidenceScore";
import DFMCheckItem from "./DFMCheckItem";

export default function DFMReport({ report }) {
  if (!report) return null;
  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6">
        <div className="grid gap-6 md:grid-cols-[220px_1fr]">
          <ConfidenceScore score={Math.round(report.score || 0)} />
          <div>
            <div className="text-xl font-semibold">Gemini Assessment</div>
            <p className="mt-3 text-muted">{report.ai_summary}</p>
            <div className="mt-4 text-sm">Fabrication success probability: {report.fabrication_success_probability}%</div>
          </div>
        </div>
      </div>
      <div className="grid gap-4">
        {report.checks?.map((check) => <DFMCheckItem key={check.name} check={check} />)}
      </div>
    </div>
  );
}
