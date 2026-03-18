export default function ConfidenceScore({ score = 0 }) {
  const safeScore = Math.max(0, Math.min(100, score || 0));
  const stroke = safeScore > 75 ? "#1f8f6b" : safeScore > 50 ? "#d48a23" : "#c44f4f";
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (safeScore / 100) * circumference;
  const isEmpty = safeScore === 0;

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center">
        <div className="w-full max-w-[220px] rounded-[1.75rem] border border-border/70 bg-white/70 p-6 text-center shadow-paper">
          <div className="font-serif text-2xl text-text">Standby</div>
          <div className="mt-2 text-sm leading-7 text-muted">
            Verification details will appear here once a real run starts.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center">
      <div className="relative rounded-full bg-white/55 p-3 shadow-paper">
        <svg width="140" height="140" className="-rotate-90">
          <circle cx="70" cy="70" r={radius} stroke="rgba(96,113,126,0.16)" strokeWidth="10" fill="none" />
          <circle cx="70" cy="70" r={radius} stroke={stroke} strokeWidth="10" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-serif text-3xl text-text">{`${safeScore}%`}</div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-muted">Confidence</div>
        </div>
      </div>
    </div>
  );
}
