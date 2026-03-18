# Nexus Agents Guide

## Project overview

Nexus is an AI-driven PCB workflow that turns a hardware description into structured requirements, a BOM, datasheet metadata, a schematic, a board layout, DFM validation, and fabrication outputs.

## Dual-LLM architecture

- Groq acts as the generator.
- Gemini acts as the verifier and design reviewer.
- Ollama is an optional local fallback for offline workflows.
- Verification loops until the confidence threshold or round limit is reached.

## Pipeline steps

- `requirements_parser.py`: converts natural language into validated requirements.
- `bom_generator.py`: builds a purchasable BOM and normalizes footprints.
- `datasheet_fetcher.py`: caches PDFs and extracts pin/package data.
- `schematic_synthesizer.py`: produces a verified netlist and KiCad schematic.
- `pcb_router.py`: places components and creates a starter board.
- `dfm_validator.py`: checks the board against fabrication rules.
- `gerber_exporter.py`: generates fabrication archives with `kicad-cli`.

## Coding conventions

- Use Python 3.11.
- Keep public code fully typed and documented.
- Use Pydantic v2 for API and pipeline models.
- Preserve `footprint_generator.py` unless explicitly told otherwise.

## Adding a new LLM provider

1. Implement `BaseLLMProvider`.
2. Add any config keys to `src/pcbai/core/config.py`.
3. Register the provider in `src/pcbai/llm/provider.py`.
4. Expose a reliable `test_connection()` method.

## Adding a new pipeline step

1. Define validated input and output models.
2. Expose a Python function and CLI/API integration.
3. Add Rich output for local operator visibility.
4. Update docs if the UI or CLI surface changes.

## KiCad compatibility

- Target KiCad 7+ for `kicad-cli`.
- Treat generated files as production starters, not final layout authority.
- Keep fab-facing outputs inspectable and deterministic.
