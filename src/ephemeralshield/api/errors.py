"""
EphemeralShield — Centralized Error Handling.

All error-to-HTTP mapping lives here. Route handlers raise domain exceptions;
this module catches them and returns structured JSON error responses.

WHY centralize errors?
  The development plan (§1.4) requires: "Centralize configuration and
  error-to-HTTP mapping." Without this:
    - Every route handler would need its own try/except blocks
    - Error response formats would be inconsistent
    - Sensitive information might leak in unhandled exceptions

HTTP status code conventions (from §3.3):
  - 401: Missing/invalid identity
  - 403: Forbidden action
  - 404: Inaccessible object
  - 409: Conflicting replay/state
  - 422: Invalid input (FastAPI handles this automatically via Pydantic)
  - 429: Quota/rate limit exceeded
  - 503: Safe issuance unavailable

Phase 1: Only basic error structures.
Phase 2+: Domain exceptions and their HTTP mappings will be added here.
"""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Structured error response body.

    Every error response from EphemeralShield follows this format.
    This makes it easy for CLI clients to parse errors programmatically.

    Fields:
        error_code: Machine-readable error code (e.g., "LEASE_EXPIRED")
        message: Human-readable description
        details: Optional additional context (never contains secrets)
    """

    error_code: str
    message: str
    details: dict[str, Any] | None = None
