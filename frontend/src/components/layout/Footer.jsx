export default function Footer() {
  return (
    <footer className="mt-10 rounded-[2rem] border border-border/70 bg-card/75 px-6 py-5 text-sm text-muted shadow-paper">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <span className="font-semibold text-text">Nexus</span> blends AI circuit generation, verification, and fabrication prep into one calm workspace.
        </div>
        <div>Frontend on Vercel. Backend on Render or local FastAPI. Ollama remains optional for local model runs.</div>
      </div>
    </footer>
  );
}
