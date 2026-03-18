export default function Footer() {
  return (
    <footer className="mt-10 rounded-[2rem] border border-border/70 bg-card/85 px-6 py-6 text-sm text-muted shadow-paper">
      <div className="grid gap-6 md:grid-cols-[1.2fr_0.8fr_0.8fr]">
        <div>
          <div className="font-serif text-xl text-text">Nexus</div>
          <div className="mt-2 leading-7">
            AI-assisted PCB generation, verification, and fabrication prep in one refined workspace.
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Stack</div>
          <div className="mt-2 leading-7">Frontend on Vercel. Backend on Render or local FastAPI.</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Models</div>
          <div className="mt-2 leading-7">Groq and Gemini in the cloud, with Ollama available when you want local runs.</div>
        </div>
      </div>
    </footer>
  );
}
