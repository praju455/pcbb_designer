import { useMemo, useState } from "react";
import PageIntro from "../components/layout/PageIntro";
import { useConfig } from "../hooks/useConfig";

export default function Settings() {
  const { configQuery, healthQuery, updateMutation } = useConfig();
  const config = configQuery.data || {};
  const [form, setForm] = useState({});
  const current = useMemo(() => ({ ...config, ...form }), [config, form]);

  return (
    <div className="space-y-6">
      <PageIntro
        eyebrow="Settings"
        title="Tune models, paths, and local fallback without losing the visual rhythm."
        description="This page keeps the same editorial structure as the rest of Nexus while still exposing the wiring you need for Groq, Gemini, Render, and optional Ollama."
      />
      <div className="glass rounded-[2rem] p-6">
        <div className="mb-4 font-serif text-2xl">Model and runtime settings</div>
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4">
            <input placeholder="Groq API key" value={current.groq_api_key || ""} onChange={(event) => setForm((prev) => ({ ...prev, GROQ_API_KEY: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
            <input placeholder="Groq model" value={current.groq_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, GROQ_MODEL: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
            <input placeholder="Gemini API key" value={current.gemini_api_key || ""} onChange={(event) => setForm((prev) => ({ ...prev, GEMINI_API_KEY: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
            <input placeholder="Gemini model (gemini-2.0-flash)" value={current.gemini_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, GEMINI_MODEL: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
          </div>
          <div className="space-y-4">
            <input placeholder="Ollama base URL" value={current.ollama_base_url || ""} onChange={(event) => setForm((prev) => ({ ...prev, OLLAMA_BASE_URL: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
            <input placeholder="Ollama model" value={current.ollama_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, OLLAMA_MODEL: event.target.value }))} className="w-full rounded-[1.25rem] border border-border/80 bg-white/70 p-3.5" />
            <div className="rounded-[1.5rem] border border-border/80 bg-white/70 p-4 text-sm text-muted">
              Local Ollama quickstart:
              <div className="mt-2 font-mono text-xs text-text">ollama serve</div>
              <div className="font-mono text-xs text-text">ollama pull mistral</div>
              <div className="font-mono text-xs text-text">ollama pull llama3.1</div>
            </div>
          </div>
        </div>
        <button onClick={() => updateMutation.mutate(form)} className="mt-6 rounded-[1.25rem] bg-text px-5 py-3 font-semibold text-background">Save settings</button>
      </div>
      <div className="glass rounded-[2rem] p-6 text-sm text-muted">
        Backend status: {healthQuery.isLoading ? "connecting" : healthQuery.data?.version ? "connected" : "offline"}
      </div>
    </div>
  );
}
