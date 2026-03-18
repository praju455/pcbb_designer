export default function ConfidenceScore({ score = 0 }) {
  const stroke = score > 75 ? "#22c55e" : score > 50 ? "#f59e0b" : "#ef4444";
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return (
    <div className="flex items-center justify-center">
      <div className="relative">
        <svg width="140" height="140" className="-rotate-90">
          <circle cx="70" cy="70" r={radius} stroke="rgba(255,255,255,0.08)" strokeWidth="10" fill="none" />
          <circle cx="70" cy="70" r={radius} stroke={stroke} strokeWidth="10" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-3xl font-semibold">{score}%</div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted">Verified</div>
        </div>
      </div>
    </div>
  );
}
