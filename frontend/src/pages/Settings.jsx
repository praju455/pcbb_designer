import { useMemo, useState } from "react";
import { useConfig } from "../hooks/useConfig";

export default function Settings() {
  const { configQuery, healthQuery, updateMutation } = useConfig();
  const config = configQuery.data || {};
  const [form, setForm] = useState({});
  const current = useMemo(() => ({ ...config, ...form }), [config, form]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6">
        <div className="mb-4 text-xl font-semibold">Nexus Control Plane</div>
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4">
            <input placeholder="Groq API key" value={current.groq_api_key || ""} onChange={(event) => setForm((prev) => ({ ...prev, GROQ_API_KEY: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
            <input placeholder="Groq model" value={current.groq_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, GROQ_MODEL: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
            <input placeholder="Gemini API key" value={current.gemini_api_key || ""} onChange={(event) => setForm((prev) => ({ ...prev, GEMINI_API_KEY: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
            <input placeholder="Gemini model" value={current.gemini_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, GEMINI_MODEL: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
          </div>
          <div className="space-y-4">
            <input placeholder="Ollama base URL" value={current.ollama_base_url || ""} onChange={(event) => setForm((prev) => ({ ...prev, OLLAMA_BASE_URL: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
            <input placeholder="Ollama model" value={current.ollama_model || ""} onChange={(event) => setForm((prev) => ({ ...prev, OLLAMA_MODEL: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-black/20 p-3" />
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-muted">
              Local Ollama quickstart:
              <div className="mt-2 font-mono text-xs text-text">ollama serve</div>
              <div className="font-mono text-xs text-text">ollama pull mistral</div>
              <div className="font-mono text-xs text-text">ollama pull llama3.1</div>
            </div>
          </div>
        </div>
        <button onClick={() => updateMutation.mutate(form)} className="mt-6 rounded-2xl bg-primary px-5 py-3 font-semibold text-black">Save Settings</button>
      </div>
      <div className="glass rounded-3xl p-6 text-sm text-muted">
        Backend status: {healthQuery.data?.version ? "connected" : "offline"} | Groq: {healthQuery.data?.groq_status || "unknown"} | Gemini: {healthQuery.data?.gemini_status || "unknown"}
      </div>
    </div>
  );
}
