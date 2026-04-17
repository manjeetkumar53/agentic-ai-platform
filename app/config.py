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
    input_price_per_1m: float
    output_price_per_1m: float
    max_attempts: int
    breaker_failure_threshold: int
    breaker_recovery_timeout_s: float
    telemetry_db: str


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        model_provider=os.getenv("MODEL_PROVIDER", "mock").lower(),
        enable_fake_long_term_memory=(
            os.getenv("ENABLE_FAKE_LONG_TERM_MEMORY", "true").lower() == "true"
        ),
        input_price_per_1m=float(os.getenv("INPUT_PRICE_PER_1M", "0.15")),
        output_price_per_1m=float(os.getenv("OUTPUT_PRICE_PER_1M", "0.60")),
        max_attempts=int(os.getenv("MAX_ATTEMPTS", "2")),
        breaker_failure_threshold=int(os.getenv("BREAKER_FAILURE_THRESHOLD", "3")),
        breaker_recovery_timeout_s=float(os.getenv("BREAKER_RECOVERY_TIMEOUT_S", "15")),
        telemetry_db=os.getenv("TELEMETRY_DB", "telemetry.db"),
    )
