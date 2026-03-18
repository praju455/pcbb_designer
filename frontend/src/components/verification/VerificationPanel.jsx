import ConfidenceScore from "./ConfidenceScore";

export default function VerificationPanel({ verificationData = {}, isLive = false }) {
  const issuesFound = verificationData.issues_found?.length || 0;
  const issuesFixed = verificationData.issues_fixed?.length || 0;
  const hasData = issuesFound > 0 || issuesFixed > 0 || (verificationData.confidence_score || 0) > 0;

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.4em] text-primary">Nexus Mesh</div>
          <div className="font-serif text-2xl">Verification loop</div>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs ${isLive ? "bg-primary/15 text-primary" : "bg-success/15 text-success"}`}>{isLive ? "Live" : hasData ? "Verified" : "Standby"}</div>
      </div>
      <div className="grid gap-6 md:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          <div className="rounded-[1.5rem] border border-border/70 bg-white/60 p-4 leading-7 text-muted">
            Groq drafts the structure, Gemini challenges it, and Nexus keeps the loop moving until the board feels safer to build.
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-4 text-sm">
              <div className="text-xs uppercase tracking-[0.28em] text-muted">Rounds</div>
              <div className="mt-2 text-2xl text-text">{verificationData.rounds_taken || 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-4 text-sm">
              <div className="text-xs uppercase tracking-[0.28em] text-muted">Found</div>
              <div className="mt-2 text-2xl text-text">{issuesFound}</div>
            </div>
            <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-4 text-sm">
              <div className="text-xs uppercase tracking-[0.28em] text-muted">Fixed</div>
              <div className="mt-2 text-2xl text-text">{issuesFixed}</div>
            </div>
          </div>
        </div>
        <ConfidenceScore score={verificationData.confidence_score || 0} />
      </div>
    </div>
  );
}
