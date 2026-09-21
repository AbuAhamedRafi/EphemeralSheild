# EphemeralShield

**PostgreSQL just-in-time credential broker** — provision short-lived, read-only database credentials on demand with automatic revocation and tamper-evident audit.

[![CI](https://github.com/ephemeralshield/ephemeralshield/actions/workflows/ci.yml/badge.svg)](https://github.com/ephemeralshield/ephemeralshield/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## What Is This?

EphemeralShield eliminates standing database credentials. Instead of giving developers permanent usernames and passwords, it provisions **time-limited, read-only PostgreSQL credentials** that automatically expire and get revoked.

### The Problem

Traditional database access:
```
Developer → permanent password → database (forever)
```
If the password leaks, the attacker has permanent access. If someone leaves the team, you need to manually rotate credentials. There's no audit trail of who accessed what.

### The Solution

EphemeralShield access:
```
Developer → mTLS certificate → request access → short-lived credential (30 min) → auto-revoke
```
- Credentials expire automatically (default: 30 minutes, max: 2 hours)
- Read-only access to explicitly approved tables
- Every access request is logged in a tamper-evident audit chain
- Revocation terminates active sessions (not just login blocks)
- Independent human approval when required by policy

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│  shieldctl  │────▶│  Nginx mTLS  │────▶│   FastAPI API     │
│  (CLI)      │     │  Proxy       │     │   (Credential     │
└─────────────┘     └──────────────┘     │    Broker)        │
                                         └────────┬──────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                        ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
                        │ broker-db │      │   Worker    │     │   Redis    │
                        │ (control  │      │ (revocation │     │ (optional  │
                        │  plane)   │      │  & cleanup) │     │  cache)    │
                        └───────────┘      └──────┬──────┘     └────────────┘
                                                   │
                                           ┌───────▼───────┐
                                           │  Target DB    │
                                           │  (your data)  │
                                           └───────────────┘
```

## Quick Start (Development)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)

### Setup

```powershell
# 1. Clone the repository
git clone https://github.com/ephemeralshield/ephemeralshield.git
cd ephemeralshield

# 2. Install Python dependencies
uv sync

# 3. Generate local development secrets
powershell -File scripts/generate-secrets.ps1

# 4. Start all Docker services (broker-db, test-target-db, redis, api)
docker compose -f deploy/compose.dev.yaml up -d --build --wait

# 5. Run database migrations
uv run alembic upgrade head

# 6. Verify everything works
uv run pytest tests/unit/ -v
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

### Available Services

| Service | URL / Port | Purpose |
|---|---|---|
| API | `http://localhost:8000` | FastAPI credential broker |
| API Docs | `http://localhost:8000/docs` | Swagger UI (dev only) |
| broker-db | `localhost:5433` | Control-plane PostgreSQL 17 |
| test-target-db | `localhost:5434` | Disposable test target PostgreSQL 17 |
| Redis | `localhost:6379` | Optional acceleration cache |

### Development Commands

```powershell
# Run linter
uv run ruff check src/ tests/

# Auto-format code
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Run unit tests
uv run pytest tests/unit/ -v

# Stop services (data preserved)
docker compose -f deploy/compose.dev.yaml down

# Stop services and DELETE all data
docker compose -f deploy/compose.dev.yaml down -v
```

## Project Structure

```
src/ephemeralshield/
├── domain/          # Core business logic (no framework imports)
├── application/     # Use cases (issue, approve, revoke, audit)
├── infrastructure/  # Database, Redis, target adapter implementations
├── api/             # FastAPI routes, dependencies, error handling
├── worker/          # Background lease expiration and revocation
├── cli/             # shieldctl — end-user CLI
├── admin/           # shield-admin — operator CLI
├── settings.py      # Centralized configuration
└── bootstrap.py     # Dependency injection (composition root)
```

## Security Guarantees & Limitations

**What EphemeralShield provides:**
- No standing human database credentials
- Time-limited, read-only access with automatic revocation
- Session termination on lease expiry (not just login blocking)
- Tamper-evident audit chain with signed checkpoints
- mTLS authentication at the network edge

**What it does NOT provide:**
- Query-level auditing (use PostgreSQL's pgaudit for that)
- Protection against a compromised client machine during an active session
- Guaranteed instant revocation (target: p99 < 5 seconds, measured not claimed)
- SOC 2/ISO 27001/HIPAA certification (describes controls, not certifications)

See [SECURITY.md](SECURITY.md) for the full threat model.

## License

[Apache License 2.0](LICENSE)

## Development Status

**Phase 1** (current): Repository structure, Docker environment, tooling ✅
**Phase 2**: PostgreSQL adapter, lease lifecycle, state machine
**Phase 3**: mTLS identity, policies, approvals, API, CLI
**Phase 4**: Revocation reliability, audit integrity, operational validation
**Phase 5**: Packaging, deployment, GitHub release
