"""Dual-LLM verification engine for generated circuit artifacts."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel

from pcbai.core.config import get_settings
from pcbai.llm.provider import get_generator_llm, get_verifier_llm
from pcbai.models import VerificationIssue, VerificationResult


class DualLLMVerifier:
    """Generate with Groq and verify with Gemini in iterative rounds."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize generator and verifier providers."""

        self.console = console or Console(stderr=True)
        self.settings = get_settings()
        self.generator = get_generator_llm()
        self.verifier = get_verifier_llm()
        self.max_rounds = self.settings.max_verification_rounds

    def _verification_schema(self) -> dict[str, Any]:
        """Return the schema expected from the verifier."""

        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                            "detail": {"type": "string"},
                            "recommendation": {"type": "string"},
                        },
                        "required": ["title", "severity", "detail", "recommendation"],
                    },
                },
                "fixes": {"type": "array", "items": {"type": "string"}},
                "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["passed", "issues", "fixes", "confidence_score"],
        }

    def _verify_payload(self, netlist: dict[str, Any], description: str) -> dict[str, Any]:
        """Ask Gemini to review the generated netlist."""

        checklist = (
            "Review this circuit/netlist and check all of the following:\n"
            "1. Pin numbers correct for each IC\n"
            "2. Missing decoupling capacitors on VCC pins\n"
            "3. Resistor values reasonable for the stated function\n"
            "4. KiCad footprint strings look valid\n"
            "5. All power and ground nets connected\n"
            "6. No floating inputs on logic ICs\n"
            "7. Correct polarities on capacitors and diodes\n"
            "8. Pull-up or pull-down resistors where needed\n"
            "9. Crystal or oscillator load capacitors if required\n"
            "10. Bypass capacitors on power pins\n"
        )
        prompt = f"{checklist}\n\nDescription:\n{description}\n\nNetlist JSON:\n{json.dumps(netlist, indent=2)}"
        return self.verifier.generate_json(prompt, self._verification_schema())

    def _fix_payload(self, description: str, current_netlist: dict[str, Any], feedback: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Ask Groq to apply verifier feedback to the current artifact."""

        prompt = (
            "You are fixing a circuit artifact after verification feedback. "
            "Return a corrected JSON artifact matching the schema.\n\n"
            f"Original description:\n{description}\n\n"
            f"Current artifact:\n{json.dumps(current_netlist, indent=2)}\n\n"
            f"Verifier feedback:\n{json.dumps(feedback, indent=2)}"
        )
        return self.generator.generate_json(prompt, schema)

    def _render_summary(self, result: VerificationResult) -> None:
        """Render the final verification summary panel."""

        filled = max(0, min(12, round(result.confidence_score / 100 * 12)))
        bar = "█" * filled + "░" * (12 - filled)
        status = "VERIFIED" if result.passed else "NEEDS REVIEW"
        issues_found = len(result.issues_found)
        issues_fixed = len(result.issues_fixed)
        panel = Panel.fit(
            "\n".join(
                [
                    "  Dual-LLM Verification Complete",
                    "",
                    f"  Generator : Groq ({result.generator_model})",
                    f"  Verifier  : Gemini ({result.verifier_model})",
                    f"  Rounds    : {result.rounds_taken}/{self.max_rounds}",
                    f"  Issues    : {issues_found} found, {issues_fixed} fixed",
                    f"  Confidence: {bar}  {result.confidence_score}%",
                    f"  Status    : {'VERIFIED' if result.passed else 'REVIEW REQUIRED'}",
                ]
            ),
            border_style="green" if result.passed else "yellow",
            title="Dual-LLM",
        )
        self.console.print(panel)

    def generate_and_verify(self, description: str, schema: dict[str, Any]) -> VerificationResult:
        """Generate an artifact and iteratively verify it."""

        self.console.print("[bold cyan]Groq generating circuit...[/bold cyan]")
        current_netlist = self.generator.generate_json(description, schema)
        issues_fixed: list[str] = []
        issues_found: list[VerificationIssue] = []
        confidence = 0
        rounds_taken = 1
        passed = False

        for round_index in range(1, self.max_rounds + 1):
            rounds_taken = round_index
            feedback = self._verify_payload(current_netlist, description)
            issues_found = [VerificationIssue.model_validate(item) for item in feedback.get("issues", [])]
            confidence = int(feedback.get("confidence_score", 0))
            self.console.print(f"[bold magenta]Gemini verifying... {len(issues_found)} issues found[/bold magenta]")

            if feedback.get("passed", False):
                passed = True
                break

            if round_index >= self.max_rounds:
                passed = False
                break

            self.console.print("[bold yellow]Groq applying fixes...[/bold yellow]")
            current_netlist = self._fix_payload(description, current_netlist, feedback, schema)
            issues_fixed.extend(feedback.get("fixes", []))

        warnings: list[str] = []
        if confidence < self.settings.min_confidence_score:
            warnings.append(
                f"Confidence score {confidence}% is below the configured minimum of {self.settings.min_confidence_score}%."
            )

        result = VerificationResult(
            netlist=current_netlist,
            confidence_score=confidence,
            rounds_taken=rounds_taken,
            issues_found=issues_found,
            issues_fixed=issues_fixed,
            generator_model=self.settings.groq_model,
            verifier_model=self.settings.gemini_model,
            passed=passed and confidence >= self.settings.min_confidence_score,
            warnings=warnings,
        )
        self._render_summary(result)
        return result

    def verify_existing(self, netlist: dict[str, Any]) -> VerificationResult:
        """Verify an already-generated netlist without running generation first."""

        feedback = self._verify_payload(netlist, "Existing netlist verification")
        issues = [VerificationIssue.model_validate(item) for item in feedback.get("issues", [])]
        confidence = int(feedback.get("confidence_score", 0))
        warnings: list[str] = []
        if confidence < self.settings.min_confidence_score:
            warnings.append(
                f"Confidence score {confidence}% is below the configured minimum of {self.settings.min_confidence_score}%."
            )

        result = VerificationResult(
            netlist=netlist,
            confidence_score=confidence,
            rounds_taken=1,
            issues_found=issues,
            issues_fixed=feedback.get("fixes", []),
            generator_model=self.settings.groq_model,
            verifier_model=self.settings.gemini_model,
            passed=bool(feedback.get("passed", False)) and confidence >= self.settings.min_confidence_score,
            warnings=warnings,
        )
        self._render_summary(result)
        return result
