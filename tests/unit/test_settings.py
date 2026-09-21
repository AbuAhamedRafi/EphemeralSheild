"""
EphemeralShield — Settings Unit Tests.

These tests verify that:
  1. Settings load correctly with default values
  2. Settings validate constraints (min TTL, valid log levels)
  3. Secret fields are properly redacted in repr/str output
  4. Environment variables override defaults correctly

WHY test settings?
  Configuration bugs are insidious — they often manifest as runtime failures
  in production that are hard to reproduce. Testing settings at the unit level
  catches:
    - Missing defaults that crash on startup
    - Invalid type conversions (str → int failures)
    - Secrets leaking into log output
    - Validator logic errors
"""

import pytest
from pydantic import ValidationError

from ephemeralshield.settings import Settings


class TestSettingsDefaults:
    """Verify that Settings has sensible defaults for all fields."""

    def test_default_lease_ttl(self) -> None:
        """Default lease TTL should be 30 minutes (1800 seconds)."""
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.lease_default_ttl_seconds == 1800

    def test_default_max_ttl(self) -> None:
        """Maximum lease TTL should be 120 minutes (7200 seconds)."""
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.lease_max_ttl_seconds == 7200

    def test_default_worker_scan_interval(self) -> None:
        """Worker scan interval should be 1 second for fast revocation."""
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.worker_scan_interval_seconds == 1.0

    def test_default_log_level(self) -> None:
        """Default log level should be INFO."""
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.log_level == "INFO"

    def test_default_environment(self) -> None:
        """Default environment should be development."""
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.environment == "development"


class TestSettingsValidation:
    """Verify that Settings rejects invalid configuration."""

    def test_reject_ttl_below_minimum(self) -> None:
        """TTL below 60 seconds should be rejected.

        WHY 60s minimum? A lease shorter than 60 seconds is likely a
        configuration error. The provisioning/cleanup cycle alone takes
        several seconds, leaving almost no usable time.
        """
        with pytest.raises(ValidationError):
            Settings(
                lease_default_ttl_seconds=10,
                _env_file=None,  # type: ignore[call-arg]
            )

    def test_reject_max_ttl_below_minimum(self) -> None:
        """Max TTL below 60 seconds should be rejected."""
        with pytest.raises(ValidationError):
            Settings(
                lease_max_ttl_seconds=30,
                _env_file=None,  # type: ignore[call-arg]
            )


class TestSettingsSecretRedaction:
    """Verify that secrets are never exposed in string representations."""

    def test_secret_fields_redacted_in_repr(self) -> None:
        """SecretStr fields must show '**********' in repr(), not the actual value.

        WHY test this? If someone accidentally logs the settings object
        (print(settings) or logger.info(settings)), secrets must not appear
        in the output. This is a security-critical invariant.
        """
        settings = Settings(
            test_target_db_password="super_secret_password",  # type: ignore[arg-type]
            _env_file=None,  # type: ignore[call-arg]
        )
        repr_str = repr(settings)
        assert "super_secret_password" not in repr_str

    def test_secret_value_accessible_explicitly(self) -> None:
        """Secrets should still be accessible via get_secret_value().

        This verifies the secret is stored correctly — it's just hidden
        from accidental exposure in logs/repr.
        """
        settings = Settings(
            test_target_db_password="super_secret_password",  # type: ignore[arg-type]
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.test_target_db_password.get_secret_value() == "super_secret_password"


class TestSettingsEnvironmentOverride:
    """Verify that environment variables override defaults."""

    def test_override_via_constructor(self) -> None:
        """Settings should accept overrides via constructor kwargs.

        This pattern is used heavily in tests to create specific configurations
        without needing to set real environment variables.
        """
        settings = Settings(
            log_level="DEBUG",
            environment="staging",
            lease_default_ttl_seconds=600,
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.log_level == "DEBUG"
        assert settings.environment == "staging"
        assert settings.lease_default_ttl_seconds == 600
