export default function ConfidenceScore({ score = 0 }) {
  const safeScore = Math.max(0, Math.min(100, score || 0));
  const stroke = safeScore > 75 ? "#1f8f6b" : safeScore > 50 ? "#d48a23" : "#c44f4f";
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (safeScore / 100) * circumference;
  const isEmpty = safeScore === 0;

  return (
    <div className="flex items-center justify-center">
      <div className="relative rounded-full bg-white/55 p-3 shadow-paper">
        <svg width="140" height="140" className="-rotate-90">
          <circle cx="70" cy="70" r={radius} stroke="rgba(96,113,126,0.16)" strokeWidth="10" fill="none" />
          {!isEmpty ? (
            <circle cx="70" cy="70" r={radius} stroke={stroke} strokeWidth="10" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
          ) : null}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-serif text-3xl text-text">{isEmpty ? "Ready" : `${safeScore}%`}</div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-muted">{isEmpty ? "Awaiting verification" : "Confidence"}</div>
        </div>
      </div>
    </div>
  );
}
