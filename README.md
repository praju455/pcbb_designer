# Nexus

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![EDA](https://img.shields.io/badge/EDA-KiCad%207%2B-0055A4.svg)

**Nexus is the AI command deck for circuit synthesis, verification, placement, and fabrication readiness.**

## What is Nexus

Nexus is a dual-LLM PCB workflow where Groq generates circuit artifacts, Gemini challenges them, and the pipeline loops until the design is stronger. It includes a CLI, a FastAPI backend, and a React control room.

## Full Architecture

```mermaid
flowchart LR
    U["User Prompt"] --> CLI["Nexus CLI"]
    U --> WEB["Nexus Frontend"]
    WEB --> API["FastAPI Backend"]
    CLI --> CORE["Pipeline Orchestrator"]
    API --> CORE

    CORE --> PARSE["Requirements Parser"]
    PARSE --> GROQ["Groq Generator"]
    GROQ --> GEMINI["Gemini Verifier"]
    GEMINI --> FIX["Groq Fix Loop"]
    FIX --> FINAL["Gemini Final Pass"]

    FINAL --> BOM["BOM Generator"]
    BOM --> DATA["Datasheet Fetcher"]
    DATA --> SCH["Schematic Synthesizer"]
    SCH --> PCB["PCB Router"]
    PCB --> DFM["DFM Validator"]
    PCB --> GERBER["Gerber Exporter"]

    DATA --> CACHE["Datasheet Cache"]
    SCH --> FILES["KiCad Schematic + Netlist"]
    PCB --> BOARD["KiCad PCB"]
    DFM --> REPORT["Fab Report + Fixes"]
    GERBER --> ZIP["Fab Package"]

    API --> WS["WebSocket Logs"]
    WS --> WEB
    WEB --> STATUS["Backend Status Button"]
    WEB --> OLLAMA["Local Ollama Controls"]
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

## .env

```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
GENERATOR_LLM=groq
VERIFIER_LLM=gemini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
KICAD_OUTPUT_DIR=./build
KICAD_CLI_PATH=kicad-cli
LOG_LEVEL=INFO
DFM_MIN_TRACE_WIDTH_MM=0.2
DFM_MIN_CLEARANCE_MM=0.2
DFM_MIN_VIA_DIAMETER_MM=0.4
JLCPCB_MIN_TRACE_WIDTH_MM=0.127
MAX_VERIFICATION_ROUNDS=3
MIN_CONFIDENCE_SCORE=75
```

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
