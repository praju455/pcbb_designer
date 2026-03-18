export default function BOMTable({ items = [] }) {
  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4 font-serif text-2xl">Bill of materials</div>
      {items.length === 0 ? (
        <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
          No BOM yet. Once a generation job completes, verified part selections will appear here.
        </div>
      ) : null}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-muted">
            <tr>
              <th className="pb-3">Ref</th>
              <th className="pb-3">Value</th>
              <th className="pb-3">Footprint</th>
              <th className="pb-3">Part</th>
              <th className="pb-3">Qty</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.reference} className="border-t border-border/60">
                <td className="py-3">{item.reference}</td>
                <td>{item.value}</td>
                <td>{item.footprint}</td>
                <td>{item.part_number}</td>
                <td>{item.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
