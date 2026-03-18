import { useEffect, useState } from "react";
import BOMTable from "../components/generator/BOMTable";
import GenerateForm from "../components/generator/GenerateForm";
import RequirementsSummary from "../components/generator/RequirementsSummary";
import SchematicPreview from "../components/generator/SchematicPreview";
import PageIntro from "../components/layout/PageIntro";
import TerminalOutput from "../components/terminal/TerminalOutput";
import VerificationPanel from "../components/verification/VerificationPanel";
import { usePipeline } from "../hooks/usePipeline";
import { useVerification } from "../hooks/useVerification";

export default function Generate() {
  const [jobId, setJobId] = useState("");
  const { generateMutation, jobQuery } = usePipeline(jobId);
  const verification = useVerification(jobQuery.data);
  const startError =
    generateMutation.error?.response?.data?.detail ||
    generateMutation.error?.message ||
    "";

  useEffect(() => {
    if (generateMutation.data?.job_id) {
      setJobId(generateMutation.data.job_id);
    }
  }, [generateMutation.data]);

  return (
    <div className="fade-rise space-y-6">
      <PageIntro
        eyebrow="Generate"
        title="Describe the circuit in plain language, then let Nexus shape the run."
        description="This workspace keeps one rhythm from start to finish: brief, queue, verification, terminal, and outputs. Nothing noisy, nothing fake."
        aside={
          <div className="space-y-4">
            <div className="text-xs uppercase tracking-[0.28em] text-muted">Current run</div>
            <div className="text-3xl font-serif text-text">{jobQuery.data?.status || "idle"}</div>
            <div className="text-sm leading-7 text-muted">
              {jobQuery.data?.current_step || "Waiting for a design brief."}
            </div>
          </div>
        }
      />
      <GenerateForm
        onSubmit={({ description, optimize, skipVerify }) => generateMutation.mutate({ description, options: { optimize, no_verify: skipVerify } })}
        isSubmitting={generateMutation.isPending}
      />
      {startError ? (
        <div className="rounded-[1.5rem] border border-error/20 bg-error/10 px-4 py-4 text-sm text-error">
          {startError}
        </div>
      ) : null}
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="glass rounded-[2rem] p-6">
          <div className="mb-4 font-serif text-2xl">Run progress</div>
          <div className="space-y-3">
            {jobQuery.data?.steps_completed?.length ? null : (
              <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
                Step timing will appear here once the backend accepts a job.
              </div>
            )}
            {(jobQuery.data?.steps_completed || []).map((step, index) => (
              <div key={step} className="flex items-center gap-3 rounded-[1.5rem] border border-success/20 bg-success/10 px-4 py-3 text-sm text-text">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-success/15 text-xs uppercase tracking-[0.18em] text-success">
                  {index + 1}
                </span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
        <VerificationPanel verificationData={verification} isLive={jobQuery.data?.status === "running"} />
      </div>
      <TerminalOutput jobId={jobId} />
      <div className="grid gap-6 xl:grid-cols-3">
        <RequirementsSummary requirements={jobQuery.data?.result?.requirements || {}} />
        <BOMTable items={jobQuery.data?.result?.bom || []} />
        <SchematicPreview files={jobQuery.data?.result?.files || []} />
      </div>
    </div>
  );
}
