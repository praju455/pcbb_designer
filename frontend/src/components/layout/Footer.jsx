export default function Footer() {
  return (
    <footer className="glass mt-8 rounded-3xl px-6 py-5 text-sm text-muted">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <span className="font-semibold text-text">Nexus</span> is the command deck for AI-assisted PCB generation, validation, and fab packaging.
        </div>
        <div>Frontend on Vercel. Backend on Render or local FastAPI. Ollama optional for local models.</div>
      </div>
    </footer>
  );
}
