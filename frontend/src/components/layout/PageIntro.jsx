export default function PageIntro({ eyebrow, title, description, aside }) {
  return (
    <section className="grid gap-6 border-b border-border/70 pb-8 lg:grid-cols-[1.3fr_0.7fr]">
      <div className="space-y-4">
        <div className="text-[11px] uppercase tracking-[0.35em] text-primary">{eyebrow}</div>
        <h1 className="max-w-3xl font-serif text-4xl leading-tight text-text md:text-5xl">{title}</h1>
        <p className="max-w-2xl text-base leading-8 text-muted">{description}</p>
      </div>
      {aside ? (
        <div className="rounded-[2rem] border border-border/80 bg-card/80 p-6 shadow-paper">
          {aside}
        </div>
      ) : null}
    </section>
  );
}
