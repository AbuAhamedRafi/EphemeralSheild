# Architecture

## Overview

EphemeralShield is a **credential broker** — it sits between developers and databases, provisioning short-lived credentials on demand. It does NOT proxy database connections; developers connect directly to the target database with their ephemeral credentials.

## Trust Boundaries

```
┌──────────────────────────────────────────────────────────────────┐
│                     Public Network / VPN                         │
│                                                                  │
│  ┌──────────────────┐                                            │
│  │  Developer        │  mTLS client certificate                  │
│  │  (shieldctl CLI)  │──────────────────────┐                    │
│  └──────────────────┘                       │                    │
│         │                                   │                    │
│         │ Ephemeral credential              │                    │
│         │ (direct SQL connection)            │                    │
│         ▼                                   ▼                    │
│  ┌──────────────────┐              ┌─────────────────┐           │
│  │  Target Database  │              │  Nginx mTLS     │           │
│  │  (your data)      │              │  Reverse Proxy  │           │
│  └──────────────────┘              └────────┬────────┘           │
│                                              │                    │
├──────────────────────────────────────────────┼────────────────────┤
│                     Private Network          │                    │
│                                              ▼                    │
│                                    ┌─────────────────┐           │
│                                    │  FastAPI API     │           │
│                                    │  (broker)        │           │
│                                    └────────┬────────┘           │
│                                              │                    │
│                              ┌───────────────┼───────────────┐   │
│                              ▼               ▼               ▼   │
│                     ┌────────────┐  ┌────────────┐  ┌────────┐  │
│                     │ broker-db  │  │  Worker    │  │ Redis  │  │
│                     │ (control)  │  │ (reaper)   │  │ (cache)│  │
│                     └────────────┘  └────────────┘  └────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Trust Decisions

1. **The Nginx proxy is the authentication boundary.** It terminates mTLS and forwards verified certificate metadata to the API. The API trusts headers from the proxy only.

2. **The broker has privileged target access.** A machine identity (provisioner/reaper) can create and drop roles on the target. This identity is a trust root — it must be tightly controlled.

3. **Redis is untrusted.** Even if Redis is compromised or unavailable, the system behaves correctly. Redis only provides optimization hints.

4. **Direct SQL access is intentional.** Developers connect to the target directly — EphemeralShield is a credential broker, not a SQL proxy.

## Layered Architecture

```
┌──────────────────────────────────────────┐
│              API / CLI / Worker           │  ← Entry points
├──────────────────────────────────────────┤
│              Application                 │  ← Use cases (orchestration)
├──────────────────────────────────────────┤
│              Domain                      │  ← Business rules (pure Python)
├──────────────────────────────────────────┤
│              Infrastructure              │  ← Database, Redis, Target adapter
└──────────────────────────────────────────┘
```

### Dependency Rule

Dependencies flow INWARD only:
- Domain knows nothing about the outside world
- Application depends on domain + abstract port interfaces
- Infrastructure implements those interfaces
- API/CLI/Worker call application use cases

The **composition root** (`bootstrap.py`) is the ONLY place that wires implementations to interfaces.

## Data Flow: Credential Issuance

```
1. Developer → shieldctl request --resource target-db --ttl 30m --reason "INC-402"
2. CLI → HTTPS POST /v1/access-requests (mTLS) → API
3. API → Validates identity, evaluates policy → Application use case
4. Use case → Creates request + lease in broker-db (control transaction)
5. Use case → Provisions role on target-db (target transaction)
6. Use case → Records audit event, returns credentials ONCE
7. CLI → Starts psql with ephemeral credentials (child process, no shell)
8. Worker → Scans for expired leases every 1 second
9. Worker → NOLOGIN + terminate sessions + DROP ROLE on target-db
10. Worker → Records revocation in audit chain
```

## Control Plane vs. Target

| Concern | Control Plane (broker-db) | Target (your database) |
|---|---|---|
| Purpose | Stores EphemeralShield metadata | Your application data |
| Owner | EphemeralShield | Your team |
| Schema changes | Alembic migrations | Target bootstrap scripts |
| Trust level | Full control | Limited provisioner/reaper access |
| Failure impact | No new issuance | Revocation still runs from worker |

## Phase 1 Decisions

- **PostgreSQL 17** for both broker-db and test-target-db (see ADR-002)
- **FastAPI** over gRPC (see ADR-001)
- **src-layout** to prevent import path confusion
- **Async-first** for all database operations (Psycopg 3 native async)
