function RequirementStat({ label, value }) {
  return (
    <div className="rounded-[1.25rem] border border-border/70 bg-white/70 p-4">
      <div className="text-[11px] uppercase tracking-[0.28em] text-muted">{label}</div>
      <div className="mt-2 text-xl text-text">{value}</div>
    </div>
  );
}

export default function RequirementsSummary({ requirements = {} }) {
  const components = requirements.components || [];
  const specialRequirements = requirements.special_requirements || [];
  const hasData = Object.keys(requirements).length > 0;

  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4">
        <div className="font-serif text-2xl">Requirements</div>
        <div className="mt-2 text-sm leading-7 text-muted">
          A designed summary of the brief, component intent, and electrical assumptions.
        </div>
      </div>
      {!hasData ? (
        <div className="rounded-[1.5rem] border border-dashed border-border/80 bg-white/50 px-4 py-6 text-sm text-muted">
          Once a design brief is parsed, Nexus will translate it into a structured summary here.
        </div>
      ) : (
        <div className="space-y-5">
          <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-5">
            <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Circuit</div>
            <div className="mt-2 font-serif text-2xl text-text">{requirements.circuit_name || "Untitled design"}</div>
            <p className="mt-3 text-sm leading-7 text-muted">{requirements.description || "No description returned."}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <RequirementStat label="Power" value={requirements.power_supply || "Not specified"} />
            <RequirementStat label="Frequency" value={requirements.frequency || "N/A"} />
            <RequirementStat label="Components" value={String(components.length)} />
          </div>
          <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-5">
            <div className="text-[11px] uppercase tracking-[0.28em] text-muted">Component plan</div>
            <div className="mt-4 flex flex-wrap gap-2">
              {components.length === 0 ? (
                <span className="text-sm text-muted">No components returned.</span>
              ) : (
                components.map((component, index) => (
                  <div key={`${component.name}-${index}`} className="rounded-full border border-border/70 bg-card px-3 py-2 text-sm text-text shadow-paper">
                    {component.name} · {component.value || component.type}
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="rounded-[1.5rem] border border-border/70 bg-white/70 p-5">
            <div className="text-[11px] uppercase tracking-[0.28em] text-muted">Special requirements</div>
            <div className="mt-4 space-y-2">
              {specialRequirements.length === 0 ? (
                <div className="text-sm text-muted">No special constraints captured.</div>
              ) : (
                specialRequirements.map((item, index) => (
                  <div key={`${item}-${index}`} className="rounded-[1rem] bg-background/60 px-3 py-3 text-sm text-text">
                    {item}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
