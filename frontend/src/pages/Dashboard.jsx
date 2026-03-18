import { useQuery } from "@tanstack/react-query";
import { getDesigns } from "../api/client";
import PipelineProgress from "../components/dashboard/PipelineProgress";
import QuickActions from "../components/dashboard/QuickActions";
import PageIntro from "../components/layout/PageIntro";
import VerificationPanel from "../components/verification/VerificationPanel";
import { useConfig } from "../hooks/useConfig";

export default function Dashboard() {
  const { healthQuery } = useConfig();
  const designsQuery = useQuery({ queryKey: ["designs"], queryFn: getDesigns });
  const health = healthQuery.data || {};
  const recent = (designsQuery.data || []).slice(0, 5);
  const backendLive = Boolean(health.version);

  return (
    <div className="fade-rise space-y-6">
      <PageIntro
        eyebrow="Control room"
        title="A cleaner cockpit for real circuit work."
        description="Nexus stays quiet until there is real data to show. Generate from plain language, watch the backend connect automatically, and keep fabrication steps in one consistent flow."
        aside={
          <div className="space-y-4">
            <div className="text-xs uppercase tracking-[0.28em] text-muted">System state</div>
            <div className="flex items-center gap-3">
              <span className={`h-3 w-3 rounded-full ${backendLive ? "bg-success" : healthQuery.isLoading ? "bg-warning animate-pulse-soft" : "bg-error"}`} />
              <span className="text-lg text-text">{backendLive ? "Connected" : healthQuery.isLoading ? "Connecting" : "Disconnected"}</span>
            </div>
            <div className="text-sm leading-7 text-muted">{backendLive ? "The backend is reachable and ready for jobs." : "Waiting for backend availability."}</div>
          </div>
        }
      />
      <PipelineProgress activeIndex={backendLive ? 1 : -1} />
      <VerificationPanel verificationData={{}} isLive={false} />
      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <QuickActions />
        <div className="glass rounded-[2rem] p-6">
          <div className="mb-4 font-serif text-2xl">Recent designs</div>
          <div className="space-y-3">
            {recent.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
                No generated designs yet. Your latest Nexus outputs will appear here once the backend completes a job.
              </div>
            ) : null}
            {recent.map((item) => (
              <div key={item.path} className="rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3">
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
