import { useEffect, useState } from "react";
import BOMTable from "../components/generator/BOMTable";
import GenerateForm from "../components/generator/GenerateForm";
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

  useEffect(() => {
    if (generateMutation.data?.job_id) {
      setJobId(generateMutation.data.job_id);
    }
  }, [generateMutation.data]);

  return (
    <div className="space-y-6">
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
      <GenerateForm onSubmit={({ description, optimize, skipVerify }) => generateMutation.mutate({ description, options: { optimize, no_verify: skipVerify } })} />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="glass rounded-[2rem] p-6">
          <div className="mb-4 font-serif text-2xl">Run progress</div>
          <div className="space-y-3">
            {jobQuery.data?.steps_completed?.length ? null : (
              <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
                Step timing will appear here once the backend accepts a job.
              </div>
            )}
            {(jobQuery.data?.steps_completed || []).map((step) => (
              <div key={step} className="rounded-[1.5rem] border border-success/20 bg-success/10 px-4 py-3 text-sm text-text">
                {step}
              </div>
            ))}
          </div>
        </div>
        <VerificationPanel verificationData={verification} isLive={jobQuery.data?.status === "running"} />
      </div>
      <TerminalOutput jobId={jobId} />
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="glass rounded-[2rem] p-6">
          <div className="mb-4 font-serif text-2xl">Requirements</div>
          <pre className="overflow-x-auto rounded-[1.5rem] bg-white/55 p-4 text-xs text-muted">{JSON.stringify(jobQuery.data?.result?.requirements || {}, null, 2)}</pre>
        </div>
        <BOMTable items={jobQuery.data?.result?.bom || []} />
        <SchematicPreview files={jobQuery.data?.result?.files || []} />
      </div>
    </div>
  );
}
