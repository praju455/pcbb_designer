import { useState } from "react";

export default function GenerateForm({ onSubmit }) {
  const [description, setDescription] = useState("");
  const [optimize, setOptimize] = useState("default");
  const [skipVerify, setSkipVerify] = useState(false);

  return (
    <form onSubmit={(event) => { event.preventDefault(); onSubmit({ description, optimize, skipVerify }); }} className="glass rounded-[2rem] p-6 md:p-8">
      <div className="mb-4 font-serif text-2xl">Describe the board you want Nexus to build.</div>
      <textarea
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Portable audio preamp with low-noise op-amp stage, 9V input, reverse polarity protection, and JST battery connector."
        className="min-h-44 w-full rounded-[1.5rem] border border-border/80 bg-white/70 p-5 outline-none transition focus:border-primary"
      />
      <div className="mt-5 grid gap-4 lg:grid-cols-[220px_1fr_220px]">
        <select value={optimize} onChange={(event) => setOptimize(event.target.value)} className="rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5">
          <option value="default">Default</option>
          <option value="thermal">Thermal</option>
          <option value="signal">Signal</option>
        </select>
        <label className="flex items-center gap-3 rounded-[1.25rem] border border-border/80 bg-white/70 px-4 py-3 text-sm text-muted">
          <input type="checkbox" checked={skipVerify} onChange={(event) => setSkipVerify(event.target.checked)} />
          <span>Skip verification for a faster, rougher first pass</span>
        </label>
        <button disabled={!description.trim()} className="rounded-[1.25rem] bg-text px-5 py-3 font-semibold text-background transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-50">Generate board</button>
      </div>
    </form>
  );
}
