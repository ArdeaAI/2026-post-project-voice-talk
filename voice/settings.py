"""Runtime settings loaded from the repo-root .env file.

All keys are optional. Missing keys disable the demos that need them — the
menu greys those out rather than crashing at startup.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Demo 3 — OpenAI Realtime API
    OPENAI_API_KEY: str | None = Field(default=None)

    # Demo 4 — Hume EVI 3
    HUME_API_KEY: str | None = Field(default=None)
    HUME_SECRET_KEY: str | None = Field(default=None)

    # Optional — avoids HuggingFace rate limits for model downloads
    HF_TOKEN: str | None = Field(default=None)

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_hume(self) -> bool:
        return bool(self.HUME_API_KEY) and bool(self.HUME_SECRET_KEY)

    def missing_keys_for(self, demo_id: str) -> list[str]:
        """Return the list of env vars a given demo still needs."""
        match demo_id:
            case "api_comparison":
                return [] if self.has_openai else ["OPENAI_API_KEY"]
            case "hume_emotion":
                missing: list[str] = []
                if not self.HUME_API_KEY:
                    missing.append("HUME_API_KEY")
                if not self.HUME_SECRET_KEY:
                    missing.append("HUME_SECRET_KEY")
                return missing
            case _:
                return []
