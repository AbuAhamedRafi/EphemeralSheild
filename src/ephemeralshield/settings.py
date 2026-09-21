"""
EphemeralShield — Application Settings.

Centralized configuration using pydantic-settings. All configuration comes from
environment variables (or a .env file in development). This is the ONLY place
that reads environment variables — no other module should call os.getenv().

WHY pydantic-settings instead of raw os.getenv()?
  1. Type safety — values are validated and converted (str → int, str → URL)
  2. Default values — documented in one place
  3. Secret redaction — SecretStr fields are never printed in logs or repr()
  4. Validation — malformed config fails fast at startup, not at runtime

WHY centralize config?
  The development plan (§1.4) requires: "No hardcoded hosts, credentials, TTLs,
  or environment-specific paths." Every configurable value lives here.

Usage:
    from ephemeralshield.settings import get_settings
    settings = get_settings()
    print(settings.broker_db_url)  # ✓ type-safe
    print(settings.broker_db_url)  # ✓ validated at startup
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    All fields map to environment variables. Field names are automatically
    converted to UPPER_CASE for env var lookup (e.g., broker_db_url → BROKER_DB_URL).

    SecretStr fields never appear in:
      - repr() / str() output
      - FastAPI's auto-generated docs
      - Log messages (if you accidentally log the settings object)
      - Exception messages

    To get the actual secret value, use: settings.broker_db_password.get_secret_value()
    """

    # -------------------------------------------------------------------------
    # Model configuration
    # -------------------------------------------------------------------------
    # env_file: Reads .env in development. In production (Docker), env vars
    #   are injected by the container runtime, so .env is not needed.
    # env_file_encoding: Explicit UTF-8 to avoid Windows encoding issues.
    # case_sensitive=False: BROKER_DB_URL and broker_db_url both work.
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars (e.g., PATH, HOME)
    )

    # -------------------------------------------------------------------------
    # Control-plane database (broker-db)
    # -------------------------------------------------------------------------
    broker_db_url: str = (
        "postgresql+psycopg://ephemeralshield:ephemeralshield_dev@broker-db:5432/ephemeralshield"
    )

    # -------------------------------------------------------------------------
    # Redis (optional acceleration)
    # -------------------------------------------------------------------------
    redis_url: str = "redis://redis:6379/0"

    # -------------------------------------------------------------------------
    # Lease configuration
    # -------------------------------------------------------------------------
    # DEFAULT: Applied when the user doesn't specify a TTL.
    # MAX: Absolute ceiling that no policy can exceed.
    # Values in seconds: 1800 = 30 min, 7200 = 120 min (2 hours).
    # -------------------------------------------------------------------------
    lease_default_ttl_seconds: int = 1800
    lease_max_ttl_seconds: int = 7200

    # -------------------------------------------------------------------------
    # Worker configuration
    # -------------------------------------------------------------------------
    # How often the background worker scans for expired leases.
    # 1.0s is aggressive but needed for the p99 < 5s revocation target (§1.2.3).
    # -------------------------------------------------------------------------
    worker_scan_interval_seconds: float = 1.0

    # -------------------------------------------------------------------------
    # Audit chain
    # -------------------------------------------------------------------------
    audit_signing_key_path: str = "./secrets/audit-signing.key"

    # -------------------------------------------------------------------------
    # Application settings
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    environment: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"  # noqa: S104 — Bind to all interfaces inside Docker
    app_port: int = 8000

    # -------------------------------------------------------------------------
    # Test target (only used in integration tests)
    # -------------------------------------------------------------------------
    test_target_db_host: str = "test-target-db"
    test_target_db_port: int = 5432
    test_target_db_user: str = "target_admin"
    test_target_db_password: SecretStr = SecretStr("target_dev_password")
    test_target_db_name: str = "target_app"

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("lease_max_ttl_seconds")
    @classmethod
    def max_ttl_must_be_positive(cls, v: int) -> int:
        """Ensure maximum TTL is at least 60 seconds."""
        if v < 60:
            msg = "lease_max_ttl_seconds must be at least 60"
            raise ValueError(msg)
        return v

    @field_validator("lease_default_ttl_seconds")
    @classmethod
    def default_ttl_must_be_positive(cls, v: int) -> int:
        """Ensure default TTL is at least 60 seconds."""
        if v < 60:
            msg = "lease_default_ttl_seconds must be at least 60"
            raise ValueError(msg)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    WHY lru_cache?
      Settings are read once at startup. Caching avoids re-reading .env and
      re-validating on every request. The cache is process-level, so each
      Uvicorn worker gets its own cached instance.

    WHY maxsize=1?
      There's only ever one Settings instance per process.
    """
    return Settings()
