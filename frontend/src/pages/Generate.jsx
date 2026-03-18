import { useEffect, useState } from "react";
import BOMTable from "../components/generator/BOMTable";
import GenerateForm from "../components/generator/GenerateForm";
import SchematicPreview from "../components/generator/SchematicPreview";
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
      <GenerateForm onSubmit={({ description, optimize, skipVerify }) => generateMutation.mutate({ description, options: { optimize, no_verify: skipVerify } })} />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="glass rounded-3xl p-6">
          <div className="mb-4 text-xl font-semibold">Pipeline Progress</div>
          <div className="space-y-3">
            {(jobQuery.data?.steps_completed || []).map((step) => (
              <div key={step} className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm">
                {step}
              </div>
            ))}
          </div>
        </div>
        <VerificationPanel verificationData={verification} isLive={jobQuery.data?.status === "running"} />
      </div>
      <TerminalOutput jobId={jobId} />
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="glass rounded-3xl p-6">
          <div className="mb-4 text-xl font-semibold">Parsed Requirements</div>
          <pre className="overflow-x-auto text-xs text-muted">{JSON.stringify(jobQuery.data?.result?.requirements || {}, null, 2)}</pre>
        </div>
        <BOMTable items={jobQuery.data?.result?.bom || []} />
        <SchematicPreview files={jobQuery.data?.result?.files || []} />
      </div>
    </div>
  );
}
