"""Read connection settings for the course's OpenAI-compatible LiteLLM Proxy.

This file is given to students as-is. Reading a few environment variables isn't
part of the lesson -- the Model boundary is.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    default_model: str
    request_timeout_seconds: float


def load_settings() -> Settings:
    base_url = os.environ.get("PHI_BASE_URL")
    api_key = os.environ.get("PHI_API_KEY")
    default_model = os.environ.get("PHI_DEFAULT_MODEL")
    if not base_url or not api_key or not default_model:
        raise RuntimeError(
            "missing PHI_BASE_URL, PHI_API_KEY, or PHI_DEFAULT_MODEL -- copy .env.example to "
            ".env and fill in your course credentials"
        )
    timeout = float(os.environ.get("PHI_REQUEST_TIMEOUT_SECONDS", "180"))
    return Settings(
        base_url=base_url,
        api_key=api_key,
        default_model=default_model,
        request_timeout_seconds=timeout,
    )
