import { useState } from "react";
import { exportGerbers } from "../api/client";
import PageIntro from "../components/layout/PageIntro";
import FileDownload from "../components/shared/FileDownload";

export default function Export() {
  const [path, setPath] = useState("");
  const [files, setFiles] = useState([]);

  return (
    <div className="fade-rise space-y-6">
      <PageIntro
        eyebrow="Export"
        title="Package fabrication files with the same quiet workflow."
        description="Once a board is ready, export Gerbers and drill outputs here. The download area stays empty until a real export returns from the backend."
      />
      <div className="glass rounded-[2rem] p-6">
        <div className="mb-4 font-serif text-2xl">Fabrication export</div>
        <div className="grid gap-4 md:grid-cols-[1fr_180px]">
          <input value={path} onChange={(event) => setPath(event.target.value)} placeholder="build/design.kicad_pcb" className="rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
          <button onClick={async () => setFiles((await exportGerbers(path, { zip: true })).files || [])} className="rounded-[1.25rem] bg-text px-5 py-3 font-semibold text-background">
            Export
          </button>
        </div>
      </div>
      <div className="glass rounded-[2rem] p-6">
        <div className="mb-4 font-serif text-2xl">Downloads</div>
        <div className="grid gap-3 md:grid-cols-2">
          {files.length === 0 ? (
            <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
              Exported files will appear here after a successful backend job.
            </div>
          ) : null}
          {files.map((file) => <FileDownload key={file} label={file.split("/").pop()} path={file} />)}
        </div>
      </div>
    </div>
  );
}
