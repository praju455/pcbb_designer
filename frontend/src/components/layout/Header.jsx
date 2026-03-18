import { MoveRight } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/generate", label: "Generate" },
  { to: "/validate", label: "Validate" },
  { to: "/export", label: "Export" }
];

export default function Header({ health, healthQuery }) {
  const connectionState = healthQuery.isLoading ? "connecting" : health ? "connected" : "disconnected";
  const statusClass =
    connectionState === "connected"
      ? "bg-success"
      : connectionState === "connecting"
        ? "bg-warning animate-pulse-soft"
        : "bg-error";
  const statusLabel =
    connectionState === "connected"
      ? "Backend connected"
      : connectionState === "connecting"
        ? "Connecting"
        : "Backend disconnected";

  return (
    <header className="mb-6 rounded-[2rem] border border-border/70 bg-card/80 px-5 py-5 shadow-paper backdrop-blur md:px-8">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-[1.35rem] border border-border/80 bg-white/70 shadow-paper">
            <img src="/nexus-mark.svg" alt="Nexus" className="h-11 w-11" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.45em] text-primary">Nexus</div>
            <h1 className="font-serif text-2xl leading-tight md:text-[2rem]">Circuit design with a calmer, sharper workflow.</h1>
          </div>
        </div>
        <div className="flex flex-col gap-4 lg:items-end">
          <nav className="flex flex-wrap items-center gap-3 text-sm text-muted">
            {links.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `ink-link rounded-full px-3 py-2 transition ${
                    isActive ? "bg-primary/10 text-text" : "hover:bg-white/60 hover:text-text"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 rounded-full border border-border/80 bg-white/70 px-4 py-2 text-sm text-muted">
            <span className={`h-2.5 w-2.5 rounded-full ${statusClass}`} />
            <span>{statusLabel}</span>
            <MoveRight size={14} className="text-primary" />
            <span className="text-text">{health?.version ? "Auto-sync active" : "Waiting for API"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
