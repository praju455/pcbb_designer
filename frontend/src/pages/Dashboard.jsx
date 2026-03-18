import { useQuery } from "@tanstack/react-query";
import { getDesigns } from "../api/client";
import QuickActions from "../components/dashboard/QuickActions";
import PipelineProgress from "../components/dashboard/PipelineProgress";
import StatusCard from "../components/dashboard/StatusCard";
import VerificationPanel from "../components/verification/VerificationPanel";
import { useConfig } from "../hooks/useConfig";

export default function Dashboard() {
  const { configQuery, healthQuery } = useConfig();
  const designsQuery = useQuery({ queryKey: ["designs"], queryFn: getDesigns });
  const config = configQuery.data || {};
  const health = healthQuery.data || {};
  const recent = (designsQuery.data || []).slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-4">
        <StatusCard title="Generator" value={config.generator_llm || "Groq"} subtitle={config.groq_model || "llama-3.3-70b-versatile"} status={health.groq_status === "ok" ? "ok" : "error"} />
        <StatusCard title="Verifier" value={config.verifier_llm || "Gemini"} subtitle={config.gemini_model || "gemini-2.5-flash"} status={health.gemini_status === "ok" ? "ok" : "error"} />
        <StatusCard title="Backend" value={health.version ? "Connected" : "Offline"} subtitle="Render or local FastAPI" status={health.version ? "ok" : "error"} />
        <StatusCard title="Designs" value={`${recent.length}`} subtitle="Recent outputs" status="idle" />
      </div>
      <PipelineProgress activeIndex={4} />
      <VerificationPanel verificationData={{ confidence_score: 88, rounds_taken: 2, issues_found: ["Pin audit", "Bypass cap"], issues_fixed: ["Footprint normalized", "Cap inserted"] }} />
      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <QuickActions />
        <div className="glass rounded-3xl p-6">
          <div className="mb-4 text-xl font-semibold">Recent Nexus Designs</div>
          <div className="space-y-3">
            {recent.map((item) => (
              <div key={item.path} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                <div>{item.name}</div>
                <div className="text-xs text-muted">{item.path}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
