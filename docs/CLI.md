# Nexus CLI Guide

## Core commands

- `pcb info`
- `pcb generate "your circuit idea"`
- `pcb verify --input build/design.netlist.json`
- `pcb validate --input build/design.kicad_pcb --fab jlcpcb`
- `pcb export --input build/design.kicad_pcb --output build/gerbers`

## Typical flow

1. Run `pcb info` to confirm Groq, Gemini, and KiCad status.
2. Run `pcb generate` with your board description.
3. Inspect the generated files in `build/`.
4. Run `pcb validate` before any fabrication export.
5. Run `pcb export` to package Gerbers and drills.

## Ollama local use

```bash
ollama serve
ollama pull mistral
```

Then set:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```
