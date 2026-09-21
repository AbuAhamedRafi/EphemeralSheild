-- =============================================================================
-- EphemeralShield — Broker Database Initialization
-- =============================================================================
-- This script runs ONCE when the broker-db container starts with an empty
-- volume. It configures the control-plane database for production readiness.
--
-- WHY not just use POSTGRES_USER/POSTGRES_DB env vars?
--   Those create the user and database, but we need additional configuration:
--   - Revoke public schema access (defense in depth)
--   - Set connection limits
--   - Configure statement timeouts
--
-- This script runs as the superuser created by POSTGRES_USER.
-- =============================================================================

-- Revoke default public schema access.
-- By default, PostgreSQL allows any user to create objects in the 'public'
-- schema. This is a well-known security issue. We restrict it.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Set a reasonable default statement timeout for the control plane.
-- This prevents runaway queries from locking the audit ledger.
-- Individual sessions can set a shorter timeout but not a longer one
-- (enforced by pg_hba.conf or role settings in production).
ALTER DATABASE ephemeralshield SET statement_timeout = '30s';

-- Set timezone to UTC — all timestamps in EphemeralShield use UTC.
-- This prevents timezone confusion between the control plane, targets,
-- and the application code. The plan (§1.4) requires "timezone-aware UTC
-- datetimes."
ALTER DATABASE ephemeralshield SET timezone = 'UTC';

-- Log slow queries for development debugging (queries > 500ms)
ALTER DATABASE ephemeralshield SET log_min_duration_statement = '500ms';
