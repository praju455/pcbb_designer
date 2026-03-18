function buildNodeMap(bomItems) {
  return new Map(
    bomItems.map((item) => [
      item.reference,
      {
        reference: item.reference,
        value: item.value,
        type: (item.reference || "U").charAt(0).toUpperCase(),
      },
    ]),
  );
}

function classifyLane(reference) {
  if (reference?.startsWith("U")) return 0;
  if (reference?.startsWith("R")) return 1;
  if (reference?.startsWith("C")) return 2;
  if (reference?.startsWith("D")) return 3;
  return 4;
}

function buildLayout(bomItems, netlist) {
  const nodeMap = buildNodeMap(bomItems);
  const referencesFromNets = (netlist?.nets || [])
    .flatMap((net) => net.pins || [])
    .map((pin) => pin.reference)
    .filter(Boolean);
  const references = [...new Set([...referencesFromNets, ...bomItems.map((item) => item.reference)])].slice(0, 8);

  return references.map((reference, index) => {
    const node = nodeMap.get(reference) || { reference, value: reference, type: (reference || "U").charAt(0).toUpperCase() };
    const lane = classifyLane(reference);
    return {
      ...node,
      x: 74 + (index % 4) * 72,
      y: 72 + lane * 22,
    };
  });
}

function symbolAccent(type) {
  if (type === "U") return { stroke: "#146c94", fill: "#d8edf8" };
  if (type === "R") return { stroke: "#60717e", fill: "#eef3f6" };
  if (type === "C") return { stroke: "#1f8f6b", fill: "#e8f5f0" };
  if (type === "D") return { stroke: "#d48a23", fill: "#f4ece0" };
  return { stroke: "#60717e", fill: "#f8fbfd" };
}

function ComponentSymbol({ node }) {
  const accent = symbolAccent(node.type);

  if (node.type === "R") {
    return (
      <g>
        <line x1={node.x - 26} y1={node.y} x2={node.x - 12} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
        <polyline
          points={`${node.x - 12},${node.y} ${node.x - 6},${node.y - 8} ${node.x},${node.y + 8} ${node.x + 6},${node.y - 8} ${node.x + 12},${node.y}`}
          fill="none"
          stroke={accent.stroke}
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <line x1={node.x + 12} y1={node.y} x2={node.x + 26} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
      </g>
    );
  }

  if (node.type === "C") {
    return (
      <g>
        <line x1={node.x - 24} y1={node.y} x2={node.x - 8} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
        <line x1={node.x - 8} y1={node.y - 12} x2={node.x - 8} y2={node.y + 12} stroke={accent.stroke} strokeWidth="2.2" />
        <line x1={node.x + 8} y1={node.y - 12} x2={node.x + 8} y2={node.y + 12} stroke={accent.stroke} strokeWidth="2.2" />
        <line x1={node.x + 8} y1={node.y} x2={node.x + 24} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
      </g>
    );
  }

  if (node.type === "D") {
    return (
      <g>
        <line x1={node.x - 24} y1={node.y} x2={node.x - 8} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
        <polygon points={`${node.x - 8},${node.y - 12} ${node.x + 8},${node.y} ${node.x - 8},${node.y + 12}`} fill="none" stroke={accent.stroke} strokeWidth="2.2" />
        <line x1={node.x + 10} y1={node.y - 14} x2={node.x + 10} y2={node.y + 14} stroke={accent.stroke} strokeWidth="2.2" />
        <line x1={node.x + 10} y1={node.y} x2={node.x + 24} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
      </g>
    );
  }

  return (
    <g>
      <rect x={node.x - 20} y={node.y - 18} width="40" height="36" rx="8" fill={accent.fill} stroke={accent.stroke} strokeWidth="2" />
      <line x1={node.x - 32} y1={node.y} x2={node.x - 20} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
      <line x1={node.x + 20} y1={node.y} x2={node.x + 32} y2={node.y} stroke={accent.stroke} strokeWidth="2.2" />
      <line x1={node.x} y1={node.y - 30} x2={node.x} y2={node.y - 18} stroke="#1f8f6b" strokeWidth="2.2" />
      <line x1={node.x} y1={node.y + 18} x2={node.x} y2={node.y + 30} stroke="#60717e" strokeWidth="2.2" />
    </g>
  );
}

function SchematicCanvas({ nodes, netlist }) {
  const nodePositions = new Map(nodes.map((node) => [node.reference, node]));
  const nets = (netlist?.nets || []).slice(0, 8);

  return (
    <svg viewBox="0 0 360 240" className="h-60 w-full">
      <rect x="8" y="8" width="344" height="224" rx="28" fill="rgba(255,255,255,0.5)" stroke="rgba(78,110,130,0.18)" />
      <line x1="28" y1="30" x2="332" y2="30" stroke="rgba(31,143,107,0.55)" strokeWidth="3" strokeLinecap="round" />
      <line x1="28" y1="210" x2="332" y2="210" stroke="rgba(96,113,126,0.45)" strokeWidth="3" strokeLinecap="round" />
      <text x="30" y="22" fill="#1f8f6b" fontSize="11" letterSpacing="1.5">VCC</text>
      <text x="30" y="228" fill="#60717e" fontSize="11" letterSpacing="1.5">GND</text>

      {nets.map((net, index) => {
        const anchoredPins = (net.pins || []).map((pin) => ({ ...pin, node: nodePositions.get(pin.reference) })).filter((pin) => pin.node);
        if (anchoredPins.length < 2) return null;

        const start = anchoredPins[0].node;
        const end = anchoredPins[anchoredPins.length - 1].node;
        const midY = 52 + index * 18;

        return (
          <g key={net.net_name}>
            <path
              d={`M ${start.x} ${start.y - 30} L ${start.x} ${midY} L ${end.x} ${midY} L ${end.x} ${end.y - 30}`}
              fill="none"
              stroke={net.net_name === "VCC" ? "rgba(31,143,107,0.55)" : net.net_name === "GND" ? "rgba(96,113,126,0.45)" : "rgba(20,108,148,0.42)"}
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <text x={(start.x + end.x) / 2} y={midY - 4} textAnchor="middle" fill="#60717e" fontSize="9" letterSpacing="1.2">
              {net.net_name}
            </text>
          </g>
        );
      })}

      {nodes.length === 0 ? (
        <text x="180" y="122" textAnchor="middle" fill="#60717e" fontSize="14">
          No generated netlist yet
        </text>
      ) : null}

      {nodes.map((node) => (
        <g key={node.reference}>
          <ComponentSymbol node={node} />
          <text x={node.x} y={node.y + 46} textAnchor="middle" fill="#10212b" fontSize="12.5" fontWeight="600">
            {node.reference}
          </text>
          <text x={node.x} y={node.y + 60} textAnchor="middle" fill="#60717e" fontSize="9.5">
            {node.value}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function SchematicPreview({ files = [], bomItems = [], netlist = {} }) {
  const hasFiles = files.length > 0;
  const previewNodes = buildLayout(bomItems.slice(0, 8), netlist);

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4">
        <div className="font-serif text-2xl">Board preview</div>
        <div className="mt-2 text-sm leading-7 text-muted">
          A net-aware schematic preview built from the generated circuit connections.
        </div>
      </div>
      <div className="rounded-[1.75rem] border border-border/70 bg-white/70 p-5 shadow-paper">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Nexus circuit view</div>
            <div className="mt-2 font-serif text-2xl text-text">
              {hasFiles ? "Ready to review" : "Waiting for generated files"}
            </div>
          </div>
          <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-[1.35rem] border border-border/80 bg-card shadow-paper">
            <img src="/nexus-mark.svg" alt="Nexus" className="h-10 w-10" />
          </div>
        </div>
        <div className="mt-4 rounded-[1.5rem] border border-border/70 bg-background/45 p-3">
          <SchematicCanvas nodes={previewNodes} netlist={netlist} />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.25rem] bg-background/55 px-4 py-4 text-sm text-muted">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Nets</div>
            <div className="mt-2 text-text">{(netlist?.nets || []).length}</div>
          </div>
          <div className="rounded-[1.25rem] bg-background/55 px-4 py-4 text-sm text-muted">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Components</div>
            <div className="mt-2 text-text">{previewNodes.length}</div>
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
