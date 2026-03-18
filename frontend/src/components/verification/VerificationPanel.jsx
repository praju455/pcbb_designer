import ConfidenceScore from "./ConfidenceScore";

export default function VerificationPanel({ verificationData = {}, isLive = false }) {
  return (
    <div className="glass rounded-3xl p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.4em] text-primary">Nexus Mesh</div>
          <div className="text-xl font-semibold">Dual-LLM Verification</div>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs ${isLive ? "bg-primary/20 text-primary" : "bg-success/20 text-success"}`}>{isLive ? "Live" : "Ready"}</div>
      </div>
      <div className="grid gap-6 md:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            Groq crafts the circuit. Gemini audits it. Nexus loops until the design feels safe enough to fabricate.
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm">
            <div>Rounds: {verificationData.rounds_taken || 0}</div>
            <div>Issues found: {verificationData.issues_found?.length || 0}</div>
            <div>Issues fixed: {verificationData.issues_fixed?.length || 0}</div>
          </div>
        </div>
        <ConfidenceScore score={verificationData.confidence_score || 0} />
      </div>
    </div>
  );
}
