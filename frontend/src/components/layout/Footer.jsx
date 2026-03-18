export default function Footer() {
  return (
    <footer className="mt-10 rounded-[2rem] border border-border/70 bg-card/85 px-6 py-6 text-sm text-muted shadow-paper">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-[1.15rem] border border-border/80 bg-white/70 shadow-paper">
            <img src="/nexus-mark.svg" alt="Nexus" className="h-9 w-9" />
          </div>
          <div>
            <div className="font-serif text-xl text-text">Nexus</div>
            <div className="mt-2 max-w-2xl leading-7">
              AI-assisted PCB generation, verification, and fabrication prep in one refined workspace.
            </div>
          </div>
        </div>
        <div className="text-[11px] uppercase tracking-[0.28em] text-primary">
          Designed for cleaner circuit workflows
        </div>
      </div>
    </footer>
  );
}
