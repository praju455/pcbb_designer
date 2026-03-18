import { useState } from "react";

export default function GenerateForm({ onSubmit }) {
  const [description, setDescription] = useState("555 timer with LED");
  const [optimize, setOptimize] = useState("default");
  const [skipVerify, setSkipVerify] = useState(false);

  return (
    <form onSubmit={(event) => { event.preventDefault(); onSubmit({ description, optimize, skipVerify }); }} className="glass rounded-3xl p-6">
      <div className="mb-4 text-xl font-semibold">Describe your board</div>
      <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-40 w-full rounded-2xl border border-white/10 bg-black/20 p-4 outline-none transition focus:border-primary" />
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <select value={optimize} onChange={(event) => setOptimize(event.target.value)} className="rounded-2xl border border-white/10 bg-black/20 p-3">
          <option value="default">Default</option>
          <option value="thermal">Thermal</option>
          <option value="signal">Signal</option>
        </select>
        <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4">
          <input type="checkbox" checked={skipVerify} onChange={(event) => setSkipVerify(event.target.checked)} />
          <span>Skip verification</span>
        </label>
        <button className="rounded-2xl bg-success px-5 py-3 font-semibold text-black transition hover:scale-[1.02]">Generate</button>
      </div>
    </form>
  );
}
