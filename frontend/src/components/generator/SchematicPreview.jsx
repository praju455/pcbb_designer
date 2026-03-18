export default function SchematicPreview({ files = [] }) {
  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4 font-serif text-2xl">Generated files</div>
      <div className="space-y-3">
        {files.length === 0 ? (
          <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
            File outputs will appear here after Nexus finishes schematic and PCB generation.
          </div>
        ) : null}
        {files.map((file) => (
          <div key={file} className="rounded-[1.5rem] border border-border/70 bg-white/70 px-4 py-3 font-mono text-xs">
            {file}
          </div>
        ))}
      </div>
    </div>
  );
}
