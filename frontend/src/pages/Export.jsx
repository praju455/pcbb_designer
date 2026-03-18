import { useState } from "react";
import { exportGerbers } from "../api/client";
import FileDownload from "../components/shared/FileDownload";

export default function Export() {
  const [path, setPath] = useState("build/design.kicad_pcb");
  const [files, setFiles] = useState([]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6">
        <div className="mb-4 text-xl font-semibold">Fabrication Export</div>
        <div className="grid gap-4 md:grid-cols-[1fr_180px]">
          <input value={path} onChange={(event) => setPath(event.target.value)} className="rounded-2xl border border-white/10 bg-black/20 p-3" />
          <button onClick={async () => setFiles((await exportGerbers(path, { zip: true })).files || [])} className="rounded-2xl bg-success px-5 py-3 font-semibold text-black">
            Export
          </button>
        </div>
      </div>
      <div className="glass rounded-3xl p-6">
        <div className="mb-4 text-xl font-semibold">Downloads</div>
        <div className="grid gap-3 md:grid-cols-2">
          {files.map((file) => <FileDownload key={file} label={file.split("/").pop()} path={file} />)}
        </div>
      </div>
    </div>
  );
}
