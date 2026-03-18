import { Link } from "react-router-dom";

export default function QuickActions() {
  return (
    <div className="glass rounded-3xl p-6">
      <div className="mb-4 text-xl font-semibold">Quick Actions</div>
      <div className="space-y-3">
        <Link to="/generate" className="block rounded-2xl border border-white/10 bg-white/5 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Launch a new design</Link>
        <Link to="/validate" className="block rounded-2xl border border-white/10 bg-white/5 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Validate an existing board</Link>
        <Link to="/settings" className="block rounded-2xl border border-white/10 bg-white/5 px-4 py-3 transition hover:border-primary/60 hover:bg-primary/10">Tune cloud and local models</Link>
      </div>
    </div>
  );
}
