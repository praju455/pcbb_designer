export default function ConfidenceScore({ score = 0 }) {
  const stroke = score > 75 ? "#456b53" : score > 50 ? "#a9752a" : "#9b4338";
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return (
    <div className="flex items-center justify-center">
      <div className="relative rounded-full bg-white/55 p-3 shadow-paper">
        <svg width="140" height="140" className="-rotate-90">
          <circle cx="70" cy="70" r={radius} stroke="rgba(111,100,89,0.16)" strokeWidth="10" fill="none" />
          <circle cx="70" cy="70" r={radius} stroke={stroke} strokeWidth="10" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-serif text-3xl text-text">{score}%</div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-muted">Confidence</div>
        </div>
      </div>
    </div>
  );
}
