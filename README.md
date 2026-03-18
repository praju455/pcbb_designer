# Nexus

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![EDA](https://img.shields.io/badge/EDA-KiCad%207%2B-0055A4.svg)

**Nexus is the AI command deck for circuit synthesis, verification, placement, and fabrication readiness.**

## What is Nexus

Nexus is a dual-LLM PCB workflow where Groq generates circuit artifacts, Gemini challenges them, and the pipeline loops until the design is stronger. It includes a CLI, a FastAPI backend, and a React control room.

## Dual-LLM architecture

```text
User Intent
    |
    v
Groq Generator -----> draft requirements / BOM / netlist
    ^                          |
    |                          v
    +------ Gemini Verifier <- audit, fixes, confidence
                              |
                              v
                      KiCad artifacts + DFM report
```

## Quick demo

```bash
pcb info
pcb generate "555 timer with LED"
pcb validate --input build/design.kicad_pcb --fab jlcpcb
pcb export --input build/design.kicad_pcb --output build/gerbers
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
cd frontend
npm install
```

## API keys

- Groq: create a free key and place it in `.env` as `GROQ_API_KEY`.
- Gemini: create a free key and place it in `.env` as `GEMINI_API_KEY`.
- Ollama: optional local fallback. Run `ollama serve` and `ollama pull mistral`.

## Quickstart

1. Copy `.env.example` to `.env` and add your keys.
2. Start the API with `uvicorn pcbai.api.main:app --reload --port 8000`.
3. Start the frontend with `cd frontend && npm run dev`.

## Web dashboard

The frontend lives in [frontend](frontend) and is designed to deploy cleanly to Vercel. It includes:

- backend connection status
- dual-LLM verification live panel
- xterm terminal logs
- settings for Groq, Gemini, and local Ollama
- footer and motion-heavy dark UI

## Command reference

- `pcb generate "description" --optimize thermal|signal|default`
- `pcb verify --input build/design.netlist.json`
- `pcb validate --input build/design.kicad_pcb --fab jlcpcb|pcbway|generic`
- `pcb export --input build/design.kicad_pcb --output build/gerbers`
- `pcb info`

## Roadmap

- richer KiCad symbol generation
- deeper SKiDL integration
- better placement heuristics
- more fab presets
- backend split into dedicated `backend/` deploy package

## Contributing

- keep `src/pcbai/steps/footprint_generator.py` untouched unless explicitly requested
- use Pydantic v2 models for pipeline contracts
- add docstrings and type hints everywhere
- test CLI and frontend integration when changing API contracts
