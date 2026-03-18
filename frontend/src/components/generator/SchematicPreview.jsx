export default function SchematicPreview({ files = [] }) {
  const hasFiles = files.length > 0;

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4">
        <div className="font-serif text-2xl">Board preview</div>
        <div className="mt-2 text-sm leading-7 text-muted">A visual sketch of the generated board package, paired with the resulting files.</div>
      </div>
      <div className="rounded-[1.75rem] border border-border/70 bg-[#221915] p-5 text-[#f6eee2] shadow-paper">
        <div className="mb-4 flex items-center justify-between text-[11px] uppercase tracking-[0.28em] text-[#d8c6ad]">
          <span>Nexus layout sketch</span>
          <span>{hasFiles ? "Generated" : "Standby"}</span>
        </div>
        <svg viewBox="0 0 320 220" className="h-52 w-full rounded-[1.25rem] bg-[#17110e]">
          <defs>
            <linearGradient id="trace" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#d1aa79" />
              <stop offset="100%" stopColor="#6f9e81" />
            </linearGradient>
          </defs>
          <rect x="18" y="18" width="284" height="184" rx="24" fill="#251b16" stroke="#5b4535" />
          <rect x="42" y="44" width="76" height="54" rx="12" fill="#f1e3cf" opacity="0.95" />
          <rect x="132" y="34" width="58" height="58" rx="12" fill="#d5b78f" opacity="0.95" />
          <rect x="210" y="54" width="70" height="48" rx="12" fill="#f1e3cf" opacity="0.95" />
          <rect x="64" y="128" width="86" height="46" rx="12" fill="#ccb090" opacity="0.95" />
          <rect x="182" y="128" width="82" height="44" rx="12" fill="#f1e3cf" opacity="0.95" />
          <path d="M118 70H132" stroke="url(#trace)" strokeWidth="6" strokeLinecap="round" />
          <path d="M190 63H210" stroke="url(#trace)" strokeWidth="6" strokeLinecap="round" />
          <path d="M98 128V98H240V128" stroke="url(#trace)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M150 151H182" stroke="url(#trace)" strokeWidth="6" strokeLinecap="round" />
          <circle cx="98" cy="98" r="6" fill="#6f9e81" />
          <circle cx="240" cy="98" r="6" fill="#d1aa79" />
          <circle cx="150" cy="151" r="6" fill="#d1aa79" />
          <circle cx="182" cy="151" r="6" fill="#6f9e81" />
        </svg>
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
