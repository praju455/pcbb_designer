# PCB Designer AI Agent

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![KiCad](https://img.shields.io/badge/KiCad-7%2B-0055A4.svg)
![Groq](https://img.shields.io/badge/Groq-Ready-f55036.svg)

**Plain English -> Manufacturable PCB, from your terminal**

![Demo placeholder](https://img.shields.io/badge/Demo-GIF%20Coming%20Soon-ffb703.svg)

## Why it exists

Describe a circuit in plain English and the agent will turn it into structured requirements, a BOM, cached datasheets, a KiCad schematic, a placed board, and fab outputs you can validate before manufacturing.

## Sticker Wall

- "Fast LLM Brain" powered by Groq, Gemini, or Ollama, with verified model selection.
- "EDA Hands" using KiCad CLI, generated KiCad files, and optional SKiDL.
- "Factory Inspector" with built-in DFM checks and JLCPCB rule awareness.

## Installation

```bash
git clone https://github.com/praju455/pcbb_designer.git
cd pcbb-designer
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Copy the template and add your provider credentials locally:

```bash
cp .env.example .env
```

## LLM provider setup

### Groq

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### Gemini

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Ollama

```bash
ollama serve
ollama pull mistral
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

## Quickstart

```bash
pcb info
pcb generate "555 timer with LED"
pcb place --input build/design.kicad_sch && pcb validate --input build/design.kicad_pcb
```

## Command reference

```bash
pcb generate "circuit description" [--output DIR] [--provider groq|ollama|gemini]
pcb place [--input FILE] [--optimize thermal|signal|default]
pcb validate [--input FILE]
pcb export [--input FILE] [--output DIR] [--gerber] [--zip]
pcb info [--provider groq|ollama|gemini]
```

All commands support `--verbose`. `generate`, `place`, and `validate` emit JSON to stdout so they are easy to chain in scripts.

## Architecture

```text
Natural language
      |
      v
requirements_parser
      |
      v
bom_generator
      |
      v
datasheet_fetcher --> datasheet cache
      |
      v
schematic_synthesizer --> .kicad_sch + sidecar JSON
      |
      v
pcb_router --> .kicad_pcb
      |
      +--> dfm_validator
      |
      +--> gerber_exporter
```

## Available models

Run `pcb info` and the CLI will query the configured provider and show only the models your current Groq, Gemini, or Ollama environment actually exposes. The default Gemini target is the verified stable model `gemini-2.5-flash`, and the default Groq target is the verified stronger general model `llama-3.3-70b-versatile`.

## KiCad notes

- KiCad 7 or newer is recommended.
- `kicad-cli` is required for Gerber and drill export.
- Generated schematic and PCB files are starter artifacts and may need polish in the KiCad GUI for complex production work.

## Roadmap

- Better symbol and footprint mapping from datasheets.
- Real KiCad Python API integration for richer board edits.
- Improved routing heuristics and constraint solving.
- Optional FastAPI web layer for remote pipeline execution.
- More manufacturer-specific DFM rule packs.

## Contributing

- Use Python 3.11.
- Keep all pipeline I/O validated with Pydantic v2 models.
- Add type hints and docstrings to every public function and class.
- Prefer deterministic fallbacks when an LLM or external tool is unavailable.
- Run tests before opening a pull request.

## License

Released under the terms of the repository [LICENSE](LICENSE).
