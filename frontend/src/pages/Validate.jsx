import { useState } from "react";
import DFMReport from "../components/validator/DFMReport";
import { useDFM } from "../hooks/useDFM";

export default function Validate() {
  const [path, setPath] = useState("build/design.kicad_pcb");
  const [fab, setFab] = useState("jlcpcb");
  const mutation = useDFM();

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6">
        <div className="mb-4 text-xl font-semibold">DFM Validation</div>
        <div className="grid gap-4 md:grid-cols-[1fr_220px_180px]">
          <input value={path} onChange={(event) => setPath(event.target.value)} className="rounded-2xl border border-white/10 bg-black/20 p-3" />
          <select value={fab} onChange={(event) => setFab(event.target.value)} className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <option value="jlcpcb">JLCPCB</option>
            <option value="pcbway">PCBWay</option>
            <option value="generic">Generic</option>
          </select>
          <button onClick={() => mutation.mutate({ filePath: path, fabTarget: fab })} className="rounded-2xl bg-primary px-5 py-3 font-semibold text-black">
            Run
          </button>
        </div>
      </div>
      <DFMReport report={mutation.data} />
    </div>
  );
}
