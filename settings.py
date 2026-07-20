"""Read connection settings for the course's OpenAI-compatible LiteLLM Proxy.

This file is given to you as-is. Reading a few environment variables isn't part of the
lesson -- the Model boundary is.

Uses Pydantic Settings: environment configuration is untrusted input, and Pydantic is
the right tool at that parsing boundary -- a plain dataclass wouldn't validate or
coerce anything.
"""

from __future__ import annotations

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PHI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    base_url: str
    api_key: SecretStr
    default_model: str
    request_timeout_seconds: float = 180.0


def load_settings() -> Settings:
    """`Settings()` with a course-friendly error instead of a raw ValidationError."""
    try:
        return Settings()
    except ValidationError as exc:
        raise RuntimeError(
            "missing PHI_BASE_URL, PHI_API_KEY, or PHI_DEFAULT_MODEL -- copy .env.example to "
            ".env and fill in your course credentials"
        ) from exc
