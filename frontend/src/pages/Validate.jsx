import { useState } from "react";
import PageIntro from "../components/layout/PageIntro";
import DFMReport from "../components/validator/DFMReport";
import { useDFM } from "../hooks/useDFM";

export default function Validate() {
  const [path, setPath] = useState("");
  const [fab, setFab] = useState("jlcpcb");
  const mutation = useDFM();

  return (
    <div className="fade-rise space-y-6">
      <PageIntro
        eyebrow="Validate"
        title="Fabrication checks without the clutter."
        description="Point Nexus to a board file, choose the fab target, and review the DFM results in the same visual structure as the rest of the app."
      />
      <div className="glass rounded-[2rem] p-6">
        <div className="mb-4 font-serif text-2xl">DFM validation</div>
        <div className="grid gap-4 md:grid-cols-[1fr_220px_180px]">
          <input value={path} onChange={(event) => setPath(event.target.value)} placeholder="build/design.kicad_pcb" className="rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
          <select value={fab} onChange={(event) => setFab(event.target.value)} className="rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5">
            <option value="jlcpcb">JLCPCB</option>
            <option value="pcbway">PCBWay</option>
            <option value="generic">Generic</option>
          </select>
          <button onClick={() => mutation.mutate({ filePath: path, fabTarget: fab })} className="rounded-[1.25rem] bg-text px-5 py-3 font-semibold text-background">
            Run check
          </button>
        </div>
      </div>
      <DFMReport report={mutation.data} />
    </div>
  );
}
