# AGENTS.md

## Project overview

`pcb-designer-ai-agent` converts a plain-English circuit request into structured design artifacts: validated requirements, a BOM, cached datasheets, a KiCad schematic, a placed PCB, DFM validation output, and optional Gerbers.

## Pipeline steps

- `requirements_parser.py`: turns natural language into `CircuitRequirements`.
- `bom_generator.py`: maps requirements to real BOM items and writes `bom.csv`.
- `datasheet_fetcher.py`: caches PDF datasheets and extracts package-focused specs.
- `schematic_synthesizer.py`: builds a simple KiCad schematic and netlist sidecars.
- `pcb_router.py`: places footprints with a greedy optimizer and emits `.kicad_pcb`.
- `dfm_validator.py`: checks board manufacturability and JLCPCB-friendly rules.
- `gerber_exporter.py`: runs `kicad-cli` to create fab outputs.

## Coding conventions

- Use Python 3.11 features and standard library types.
- All public classes and functions must have docstrings.
- All pipeline inputs and outputs must be represented by Pydantic v2 models.
- Type hints are required across the codebase.
- Prefer ASCII source unless a terminal-facing output specifically benefits from symbols.

## Adding a new LLM provider

1. Create `src/pcbai/llm/providers/<name>_provider.py`.
2. Implement `BaseLLMProvider`.
3. Add config keys to `src/pcbai/core/config.py` and `.env.example`.
4. Register the provider in `src/pcbai/llm/provider.py`.
5. Support `list_available_models()` so `pcb info` can show only live models.

## Adding a new pipeline step

1. Define or reuse a Pydantic input model.
2. Define a Pydantic output model.
3. Keep the step callable from both Python and the CLI.
4. Print user-facing summaries with Rich when the step runs interactively.
5. Add tests for success and fallback behavior.

## Testing requirements

- Run `pytest`.
- Validate new CLI behavior with at least one happy-path test when practical.
- Preserve existing footprint generator tests.
- If a step depends on network or proprietary tools, include deterministic fallbacks so tests can run offline.

## KiCad compatibility

- Target KiCad 7+ file formats and `kicad-cli`.
- Keep generated files simple and inspectable.
- Treat KiCad Python API use as optional because many environments only have the CLI available.
