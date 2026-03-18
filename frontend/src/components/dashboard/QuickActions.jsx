import { Link } from "react-router-dom";

export default function QuickActions() {
  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4 font-serif text-2xl">Quick actions</div>
      <div className="space-y-3">
        <Link to="/generate" className="block rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Start a new board</Link>
        <Link to="/validate" className="block rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Run fabrication validation</Link>
        <Link to="/export" className="block rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Package Gerbers for fabrication</Link>
      </div>
    </div>
  );
}
