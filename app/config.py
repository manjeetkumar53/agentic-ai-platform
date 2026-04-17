from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_host: str
    app_port: int
    model_provider: str
    enable_fake_long_term_memory: bool


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        model_provider=os.getenv("MODEL_PROVIDER", "mock").lower(),
        enable_fake_long_term_memory=(
            os.getenv("ENABLE_FAKE_LONG_TERM_MEMORY", "true").lower() == "true"
        ),
    )
