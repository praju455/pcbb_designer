import { useState } from "react";
import PageIntro from "../components/layout/PageIntro";
import DFMReport from "../components/validator/DFMReport";
import { useDFM } from "../hooks/useDFM";

export default function Validate() {
  const [path, setPath] = useState("");
  const [fab, setFab] = useState("jlcpcb");
  const mutation = useDFM();
  const canRun = path.trim().length > 0 && !mutation.isPending;

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
          <input value={path} onChange={(event) => setPath(event.target.value)} placeholder="build/design.kicad_pcb" className="field-shell rounded-[1.25rem] p-3.5" />
          <select value={fab} onChange={(event) => setFab(event.target.value)} className="field-shell select-field rounded-[1.25rem] p-3.5">
            <option value="jlcpcb">JLCPCB</option>
            <option value="pcbway">PCBWay</option>
            <option value="generic">Generic</option>
          </select>
          <button
            onClick={() => mutation.mutate({ filePath: path.trim(), fabTarget: fab })}
            disabled={!canRun}
            className={`rounded-[1.25rem] px-5 py-3 font-semibold transition ${
              canRun
                ? "cursor-pointer bg-text text-background hover:-translate-y-0.5"
                : "cursor-not-allowed bg-text/35 text-background/70"
            }`}
          >
            {mutation.isPending ? "Checking..." : "Run check"}
          </button>
        </div>
        {mutation.isError && (
          <div className="mt-4 rounded-[1.25rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            Validation could not be completed. Check the board path and backend status, then try again.
          </div>
        )}
      </div>
      <DFMReport report={mutation.data} />
    </div>
  );
}
