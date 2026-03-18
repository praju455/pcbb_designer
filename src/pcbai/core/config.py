"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the PCB AI agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: Literal["groq", "ollama", "gemini", "openai"] = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama3-8b-8192", alias="GROQ_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="mistral", alias="OLLAMA_MODEL")
    kicad_output_dir: Path = Field(default=Path("./build"), alias="KICAD_OUTPUT_DIR")
    kicad_cli_path: str = Field(default="kicad-cli", alias="KICAD_CLI_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    dfm_min_trace_width_mm: float = Field(default=0.2, alias="DFM_MIN_TRACE_WIDTH_MM")
    dfm_min_clearance_mm: float = Field(default=0.2, alias="DFM_MIN_CLEARANCE_MM")
    dfm_min_via_diameter_mm: float = Field(default=0.4, alias="DFM_MIN_VIA_DIAMETER_MM")
    jlcpcb_min_trace_width_mm: float = Field(default=0.127, alias="JLCPCB_MIN_TRACE_WIDTH_MM")

    def ensure_output_dir(self) -> Path:
        """Create and return the configured KiCad output directory."""

        self.kicad_output_dir.mkdir(parents=True, exist_ok=True)
        return self.kicad_output_dir


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()
