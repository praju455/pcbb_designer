import { Cpu, Factory, LayoutDashboard, Settings, ShieldCheck, WandSparkles } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/generate", label: "Generate", icon: WandSparkles },
  { to: "/validate", label: "Validate", icon: ShieldCheck },
  { to: "/export", label: "Export", icon: Factory },
  { to: "/settings", label: "Settings", icon: Settings }
];

export default function Sidebar() {
  return (
    <aside className="glass sticky top-4 flex h-[calc(100vh-2rem)] w-72 flex-col rounded-3xl p-6 shadow-glow">
      <div className="mb-10 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/20 text-primary shadow-glow">
          <Cpu />
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.4em] text-primary">Nexus</div>
          <div className="text-lg font-semibold">Board Intelligence</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-3">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${isActive ? "bg-primary text-black shadow-glow" : "bg-white/5 hover:bg-white/10"}`}>
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-muted">
        Nexus pairs Groq, Gemini, and optional local Ollama for robust PCB synthesis.
      </div>
    </aside>
  );
}
