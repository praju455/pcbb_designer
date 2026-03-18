const steps = ["Intent", "Parse", "BOM", "Datasheet", "Schematic", "Place", "Gerber"];

export default function PipelineProgress({ activeIndex = 3 }) {
  return (
    <div className="glass rounded-[2rem] p-6">
      <div className="mb-4 font-serif text-2xl">Pipeline</div>
      <div className="grid gap-3 lg:grid-cols-7">
        {steps.map((step, index) => (
          <div key={step} className={`rounded-[1.5rem] border p-4 text-center ${index <= activeIndex ? "border-primary/40 bg-primary/10 shadow-paper" : "border-border/70 bg-white/55"}`}>
            <div className="text-xs uppercase tracking-[0.24em] text-muted">{String(index + 1).padStart(2, "0")}</div>
            <div className="mt-2 text-sm font-medium">{step}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
