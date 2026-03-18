const steps = ["Intent", "Parse", "BOM", "Datasheet", "Schematic", "Place", "Gerber"];

export default function PipelineProgress({ activeIndex = 3 }) {
  return (
    <div className="glass rounded-3xl p-6">
      <div className="mb-4 text-xl font-semibold">Nexus Flow</div>
      <div className="grid gap-4 lg:grid-cols-7">
        {steps.map((step, index) => (
          <div key={step} className={`rounded-2xl border p-4 text-center ${index <= activeIndex ? "border-primary bg-primary/10 shadow-glow" : "border-white/10 bg-white/5"}`}>
            <div className="text-sm font-medium">{step}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
