export default function BOMTable({ items = [] }) {
  return (
    <div className="glass rounded-3xl p-6">
      <div className="mb-4 text-xl font-semibold">BOM</div>
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
              <tr key={item.reference} className="border-t border-white/5">
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
