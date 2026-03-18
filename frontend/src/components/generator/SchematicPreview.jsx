export default function SchematicPreview({ files = [] }) {
  const hasFiles = files.length > 0;

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4">
        <div className="font-serif text-2xl">Generated files</div>
        <div className="mt-2 text-sm leading-7 text-muted">
          Clean references for the schematic, board, and fabrication package.
        </div>
      </div>
      <div className="rounded-[1.75rem] border border-border/70 bg-white/70 p-5 shadow-paper">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Nexus outputs</div>
            <div className="mt-2 font-serif text-2xl text-text">
              {hasFiles ? "Ready to review" : "Waiting for generated files"}
            </div>
          </div>
          <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-[1.35rem] border border-border/80 bg-card shadow-paper">
            <img src="/nexus-mark.svg" alt="Nexus" className="h-10 w-10" />
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.25rem] bg-background/55 px-4 py-4 text-sm text-muted">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Schematic</div>
            <div className="mt-2 text-text">{hasFiles ? "Generated" : "Pending"}</div>
          </div>
          <div className="rounded-[1.25rem] bg-background/55 px-4 py-4 text-sm text-muted">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">PCB</div>
            <div className="mt-2 text-text">{hasFiles ? "Generated" : "Pending"}</div>
          </div>
          <div className="rounded-[1.25rem] bg-background/55 px-4 py-4 text-sm text-muted">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Export pack</div>
            <div className="mt-2 text-text">{hasFiles ? "Available" : "Pending"}</div>
          </div>
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {!hasFiles ? (
          <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
            File outputs will appear here after Nexus finishes schematic and PCB generation.
          </div>
        ) : (
          files.map((file) => (
            <div key={file} className="rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3 font-mono text-xs">
              {file}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
