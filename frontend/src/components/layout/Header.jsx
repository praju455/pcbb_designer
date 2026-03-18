import { PlugZap, Sparkles } from "lucide-react";
import StatusBadge from "../shared/StatusBadge";

export default function Header({ health }) {
  const backendOk = Boolean(health);

  return (
    <header className="glass mb-6 flex items-center justify-between rounded-3xl px-6 py-5">
      <div>
        <div className="text-xs uppercase tracking-[0.4em] text-primary">Nexus</div>
        <h1 className="text-3xl font-semibold">Engineered circuits, cinematic workflow</h1>
      </div>
      <div className="flex items-center gap-3">
        <button className="flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 transition hover:border-primary/60 hover:bg-primary/10">
          <PlugZap size={16} />
          Backend Link
          <StatusBadge status={backendOk ? "ok" : "error"} label={backendOk ? "Connected" : "Offline"} />
        </button>
        <div className="rounded-full bg-primary/20 px-4 py-2 text-sm text-primary">
          <Sparkles className="mr-2 inline" size={16} />
          Dual-LLM Active
        </div>
      </div>
    </header>
  );
}
