export default function BOMTable({ items = [] }) {
  const totalComponents = items.reduce((sum, item) => sum + (item.quantity || 0), 0);

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="font-serif text-2xl">Bill of materials</div>
          <div className="mt-2 text-sm leading-7 text-muted">Verified selections, footprints, and sourcing hints in one place.</div>
        </div>
        <div className="rounded-[1.25rem] border border-border/70 bg-white/70 px-4 py-3 text-right">
          <div className="text-[11px] uppercase tracking-[0.28em] text-muted">Parts</div>
          <div className="mt-1 text-xl text-text">{totalComponents}</div>
        </div>
      </div>
      {items.length === 0 ? (
        <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
          No BOM yet. Once a generation job completes, verified part selections will appear here.
        </div>
      ) : null}
      <div className="overflow-x-auto rounded-[1.5rem] border border-border/70 bg-white/70 p-2">
        <table className="w-full text-left text-sm">
          <thead className="text-muted">
            <tr>
              <th className="px-3 pb-3 pt-2">Ref</th>
              <th className="px-3 pb-3 pt-2">Value</th>
              <th className="px-3 pb-3 pt-2">Footprint</th>
              <th className="px-3 pb-3 pt-2">Part</th>
              <th className="px-3 pb-3 pt-2">Qty</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.reference} className="border-t border-border/60">
                <td className="px-3 py-3 font-medium text-text">{item.reference}</td>
                <td className="px-3">{item.value}</td>
                <td className="px-3 text-xs text-muted">{item.footprint}</td>
                <td className="px-3">{item.part_number}</td>
                <td className="px-3">{item.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
