export default function SchematicPreview({ files = [] }) {
  return (
    <div className="glass rounded-3xl p-6">
      <div className="mb-4 text-xl font-semibold">Generated Files</div>
      <div className="space-y-3">
        {files.map((file) => (
          <div key={file} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 font-mono text-xs">
            {file}
          </div>
        ))}
      </div>
    </div>
  );
}
