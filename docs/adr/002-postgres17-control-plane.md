# ADR-002: PostgreSQL 17 (Stable) for Control Plane

## Status: Accepted

## Context

The development plan (§1.3) recommended PostgreSQL 18 for the control-plane database. As of September 2026, PostgreSQL 18 is in beta. We needed to decide:

1. **PostgreSQL 18 (beta)** — Latest features, but potential bugs
2. **PostgreSQL 17 (stable)** — Production-proven, fully supported

## Decision

**Use PostgreSQL 17 for all instances (broker-db, test-target-db).**

## Rationale

1. **The control plane stores security-critical data.** Audit chains, lease records, and access requests are evidence that must not be corrupted. Using a beta database for this data is an unnecessary risk.

2. **No PG 18-specific features needed.** Phase 1-3 require standard PostgreSQL capabilities: transactions, constraints, indexes, SCRAM auth, role management. All available in PG 17.

3. **Consistent version across instances.** Using PG 17 for both broker-db and test-target-db means the target adapter is tested against the same version it manages. Version-specific quirks won't create test/production gaps.

4. **Upgrade path is straightforward.** When PG 18 reaches GA and has proven stable, upgrading is a container image change + `pg_upgrade`. No application code changes needed.

## Consequences

- All PostgreSQL images use `postgres:17-alpine`
- Target adapter tests run against PG 17
- PG 18 features (if any are useful) are deferred until GA + 1 patch release
- Document PG 17 as the tested/supported version in README
