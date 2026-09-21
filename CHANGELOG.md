# Changelog

All notable changes to EphemeralShield will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Phase 1: Foundation
- Project structure with strict dependency direction (domain → application → infrastructure)
- Docker Compose development environment (broker-db, test-target-db, redis, api)
- FastAPI application factory with health check endpoints (`/health/live`, `/health/ready`)
- Centralized configuration with pydantic-settings (type-safe, secret-redacting)
- Alembic migration infrastructure with async SQLAlchemy + Psycopg 3
- Initial empty migration (001) for connectivity verification
- Test suite with settings and health endpoint unit tests
- Pre-commit hooks (Ruff, secret detection, file hygiene)
- Development secret generation scripts (PowerShell + Bash)
- Synthetic test target database with customers/orders/payments data
- Multi-stage Dockerfile (non-root, production-ready)
- Architecture Decision Records (ADR-001: FastAPI, ADR-002: PostgreSQL 17)
- Documentation: README, AGENTS.md, SECURITY.md, CONTRIBUTING.md
- Threat model and architecture documentation
