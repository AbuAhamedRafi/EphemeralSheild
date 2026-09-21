# EphemeralShield — Five-Phase Development Plan

**Objective:** Build a PostgreSQL just-in-time credential broker with FastAPI, a Python CLI, reliable revocation, and verifiable audit records. Start with your existing local `target-db`; finish with a reproducible private deployment and a documented GitHub release.

**Framework recommendation: FastAPI.** This project is primarily an asynchronous API, PostgreSQL adapter, CLI, and background worker. FastAPI fits that shape without introducing Django's admin and application framework. Use REST/JSON over HTTPS for version 1; replace the proposed gRPC service with FastAPI rather than maintaining two transports. FastAPI supports the asynchronous I/O needed here. [FastAPI concurrency documentation](https://fastapi.tiangolo.com/async/)

This document is the implementation contract. Execute the five phases in order. Each phase has a working deliverable, verification requirements, and an explicit completion gate.

## Phase 1 — Establish the repository, security contract, and local environment

### 1.1 Freeze the version 1 scope

Implement:

- One organization; registered human identities and operator-managed groups.
- Mutual TLS authentication at a dedicated reverse proxy.
- PostgreSQL targets only; your local `target-db` is the first target.
- Read-only access to explicitly approved schemas/tables or views.
- Immediate issuance when policy permits; independent human approval when required.
- A default lease of 30 minutes and a hard maximum of 120 minutes, further restricted by policy.
- One-time credential delivery, explicit revocation, scheduled expiry, and crash recovery.
- A Typer CLI named `shieldctl` and an operator CLI named `shield-admin`.
- A hash-chained issuance/authorization audit ledger with independently stored signed checkpoints.
- Separate API and worker processes, Docker Compose development and deployment, GitHub Actions, and GHCR images.

Do not add AWS credentials, MySQL, Kubernetes, Terraform, a browser dashboard, a custom SQL proxy, lease renewal, or read-write access to version 1. Record these as later milestones. Read-write migrations need a separate permissions and transaction-safety design.

### 1.2 Make the security claims precise

1. **No standing human database credentials.** A protected machine identity still needs authority to provision and revoke users. Document its ownership, rotation, and emergency recovery procedures.
2. **Password expiry is not session termination.** PostgreSQL `VALID UNTIL` expires password authentication; it does not delete the role or close an existing connection. Use password authentication for ephemeral users and actively terminate their sessions. [PostgreSQL CREATE ROLE](https://www.postgresql.org/docs/current/sql-createrole.html), [administration functions](https://www.postgresql.org/docs/current/functions-admin.html)
3. **Revocation has a measured latency.** Start with a one-second due-lease scan and a release target of p99 session termination within five seconds of expiry under the documented healthy-load test. This is a target to prove, not a claim to publish before measurement. If all revokers fail or cannot reach the target, existing sessions may outlive the lease. A hard cutoff independent of those failures requires an enforced proxy or target-side mechanism outside this release.
4. **PostgreSQL is authoritative.** Redis is an optional wake-up/cache optimization. Expiration notifications can be lost or delayed, so correctness cannot depend on them. [Redis notification semantics](https://redis.io/docs/latest/develop/pubsub/keyspace-notifications/)
5. **Issuance evidence is not query evidence.** A lease record proves authorization and issuance. Target connection logs prove observed connections. Neither alone proves which customer records were read. Query/object auditing requires a separately configured database audit facility and a defined coverage claim.
6. **A chain is tamper-evident relative to a trusted anchor.** A privileged attacker who can replace the entire ledger can recompute an unanchored chain. Export signed checkpoints to independently administered storage.
7. **Compliance is not automatic.** Describe supported controls and collected evidence; do not claim SOC 2, ISO 27001, or HIPAA certification from implementing this project.
8. **Read replicas need a separate adapter design.** Version 1 accepts writable standalone PostgreSQL targets. A physical standby cannot execute provisioning DDL; primary-side changes, replication lag, and termination on every serving endpoint require additional handling. [PostgreSQL standby documentation](https://www.postgresql.org/docs/current/warm-standby.html)

### 1.3 Choose and lock the stack

| Concern | Choice |
|---|---|
| Python | Python 3.12 baseline; lock a tested patch in toolchain/container configuration |
| Dependency management | `uv`, `pyproject.toml`, committed `uv.lock`; frozen installs in CI |
| API | FastAPI, Uvicorn, Pydantic v2, `pydantic-settings` |
| Control-plane persistence | PostgreSQL, SQLAlchemy 2 async, Alembic |
| PostgreSQL driver | Psycopg 3 async for both SQLAlchemy and direct target operations |
| CLI | Typer, HTTPX; subprocess execution without a shell |
| Worker | Dedicated asyncio process with durable PostgreSQL work claims |
| Optional acceleration | Redis async client; never the authoritative lease store |
| Authentication edge | Nginx mTLS proxy; private API network |
| Cryptography | `secrets`, SHA-256, `cryptography` Ed25519 checkpoint signatures |
| Quality | pytest, pytest-asyncio, Ruff, mypy strict, coverage, import-linter |
| Security checks | Bandit, pip-audit, secret scanning, Trivy |
| Packaging/deployment | Python wheel, multi-stage container, Docker Compose, GHCR |

Resolve supported dependency releases at implementation time, verify Python compatibility, and commit the exact lockfile. Inspect your existing PostgreSQL major version first. Use that major in target integration tests and declare only versions actually tested. Use a separate PostgreSQL 18 control-plane instance with a pinned, patched image.

### 1.4 Create the strict repository structure

Create the following paths; do not fill the project with empty placeholder classes. Add modules as their phase implements them.

```text
ephemeralshield/
  AGENTS.md
  README.md
  SECURITY.md
  CONTRIBUTING.md
  CHANGELOG.md
  LICENSE
  pyproject.toml
  uv.lock
  .python-version
  .env.example
  .gitignore
  .dockerignore
  .pre-commit-config.yaml
  Makefile
  alembic.ini
  src/ephemeralshield/
    domain/             # Plain typed entities, states, policies, errors, ports
    application/        # Issue, approve, revoke, reconcile, and audit use cases
    infrastructure/
      database/         # ORM models, repositories, unit of work
      postgres/         # Target adapter and safe SQL operations
      redis/            # Optional expiry hints and caching
      identity/         # Verified identity mapping and certificate registry
      secrets/          # Secret-reference resolver
      audit/            # Canonical encoding, append, verification, signing
      observability/    # Redaction, logging, metrics
    api/
      routes/
      schemas/
      dependencies.py
      errors.py
      app.py
    worker/
      main.py
      scheduler.py
      reaper.py
      reconciler.py
    cli/
      main.py
      client.py
      commands/
    admin/
      main.py
      commands/
    bootstrap.py        # Composition root; wires implementations to ports
    settings.py
  migrations/versions/
  sql/target-bootstrap/ # Reviewed installation/upgrade scripts, operator-run
  tests/
    unit/
    integration/
    contract/
    e2e/
    security/
    resilience/
    fixtures/
  deploy/
    Dockerfile
    compose.dev.yaml
    compose.prod.yaml
    nginx/
    monitoring/
  scripts/
  docs/
    architecture.md
    threat-model.md
    permissions.md
    configuration.md
    api.md
    development-plan.md
    progress.md
    adr/
    runbooks/
    evidence/
  examples/             # Fake identities, policies, and synthetic datasets
  .github/
    workflows/
    ISSUE_TEMPLATE/
    pull_request_template.md
    CODEOWNERS
    dependabot.yml
```

Enforce these coding rules in `AGENTS.md` and CI:

- Dependency direction: domain has no framework imports; application depends on domain and typed ports; infrastructure implements ports; API/worker/CLI call application use cases. Only the composition root wires concrete implementations.
- API routes only authenticate, validate, invoke a use case, and serialize results. No SQL, DDL, policy decisions, or background reapers inside routes.
- Use one unit of work per control-plane operation. Do not share async sessions between concurrent tasks.
- Type all application code; run mypy strict. Avoid `Any`, wildcard imports, unreviewed ignores, and broad exception suppression.
- Centralize configuration and error-to-HTTP mapping. No hardcoded hosts, credentials, TTLs, or environment-specific paths.
- Use timezone-aware UTC datetimes. Persist deadlines derived from the control database clock; monitor target/control clock skew.
- Use parameter binding for values and safe SQL composition for identifiers. Do not interpolate user input into SQL, shell commands, or connection strings. Psycopg provides explicit identifier/literal composition primitives. [Psycopg SQL composition](https://www.psycopg.org/psycopg3/docs/api/sql.html)
- Target operations have bounded connection, query, lock, and retry timeouts. Never hold a control database transaction open while waiting on target network I/O.
- Secrets must not appear in logs, exception bodies, traces, metrics, audit payloads, test snapshots, or Git history.
- All changes to persistence use Alembic migrations; no production `create_all()`.
- Document security-sensitive decisions in ADRs. No silent architecture changes, fake passing tests, or TODO implementations on active security paths.

### 1.5 Inspect and isolate your local target

1. Record the target's host, port, actual database name, PostgreSQL version, TLS mode, and whether it is in recovery. Treat `target-db` as an alias until its actual connection details are confirmed.
2. Keep business data in the target and broker metadata in a separate `broker-db` instance. Never store broker tables in the application's target database.
3. Create a disposable test target using the same PostgreSQL major as your local target. Run destructive tests only against this disposable instance.
4. For your existing target, prepare a bootstrap plan first. Check for conflicting roles, privileges, and schemas before installation. Never reset the existing volume or globally revoke existing application permissions.
5. In Docker, use service DNS for a containerized target. For a host-based target, configure the appropriate host gateway; `localhost` inside the API container is not your laptop.
6. Bind development database ports to loopback. Seed synthetic `customers`, `orders`, and `payments` data in the disposable target.

### 1.6 Produce the initial developer workflow

Implement working `make setup`, `make dev-up`, `make migrate`, `make lint`, `make typecheck`, `make test-unit`, and `make dev-down` targets. Document their `uv`/Compose equivalents for Windows users; recommend WSL2 for the Linux deployment workflow.

Commit an `.env.example` containing placeholders and secret-reference paths only. Generate local secrets outside Git with restrictive permissions. Initial health endpoints must expose no sensitive configuration.

**Phase 1 completion gate:** A clean clone installs from the lockfile, starts isolated development services, applies the initial migration, and passes lint/type/unit checks. The existing `target-db` has not been reset or used for destructive tests. Commit the architecture ADR, threat model, coding contract, and initial progress record.

**LLM instruction:** “Implement Phase 1 only. Establish the documented structure and commands, inspect the target without modifying existing business data, and record verified environment facts. Do not build issuance endpoints yet. End with changed files, exact commands run, results, and remaining blockers.”

## Phase 2 — Implement the PostgreSQL adapter and durable lease lifecycle

### 2.1 Create the control-plane schema

| Table | Required purpose and fields |
|---|---|
| `principals` | Immutable identity ID, display name, active/disabled flag |
| `principal_certificates` | Principal, trusted issuer identity, serial, validity, revoked timestamp; unique issuer/serial |
| `groups`, `group_memberships` | Operator-controlled policy membership |
| `target_resources` | Alias, cluster identity, host/port/database, TLS CA reference, provisioning-secret reference, allowed scopes, TTL limits, enabled flag, configuration version |
| `access_policies` | Group/resource/profile binding, maximum TTL, approval requirement, enabled flag, version |
| `access_requests` | Requester, reason, optional ticket, scope, requested TTL, decision, reviewer, decision expiry, policy/configuration snapshot |
| `credential_leases` | UUID, request ID, target cluster/resource, principal, generated role, state, deadline, timestamps, revocation cause, last error code, version/fencing counter |
| `work_items` | Durable operation, lease, attempt count, next attempt, claim owner/token, claim expiry, sanitized error code |
| `idempotency_records` | Principal, endpoint, key, request fingerprint, request/lease reference, expiry; never response passwords |
| `audit_ledger` | Sequence, nullable lease/request IDs, actor, action, event timestamp, canonical event bytes, previous hash, current hash |
| `audit_chain_head` | Last committed sequence/hash; locked during append |
| `audit_checkpoints` | Last independently exported signed checkpoint and verification metadata |
| `worker_heartbeats` | Worker instance, last heartbeat, capability/version |

Use foreign keys that preserve historical evidence; deactivate resources and policies instead of cascading away history. Add due-work and due-lease indexes, unique target-cluster/role constraints, TTL checks, and idempotency uniqueness constraints. Requests denied before lease creation must still be auditable.

### 2.2 Implement the state machine before orchestration

Use separate request and lease enums with these exact transitions:

| Entity | From | To | Condition |
|---|---|---|---|
| Request | New request | `APPROVED`, `PENDING_APPROVAL`, or `DENIED` | Initial policy decision; no database credential exists yet |
| Request | `PENDING_APPROVAL` | `APPROVED`, `DENIED`, or `CANCELLED` | Independent review, cancellation, or approval-window expiry |
| Request | `APPROVED` | `CONSUMED` | Atomically allocate one `PROVISIONING` lease and consume approval |
| Request | `APPROVED` | `CANCELLED` | Authorization changed, deadline passed, or requester cancelled |
| Lease | `PROVISIONING` | `ACTIVE` | Target provisioning and durable issuance audit succeeded |
| Lease | `PROVISIONING` | `FAILED` | Target role absence confirmed; no credential remains usable |
| Lease | `PROVISIONING` | `REVOKING` | Failure/cancellation with target state present or uncertain |
| Lease | `ACTIVE` | `REVOKING` | Expiry, manual revocation, or security/policy action |
| Lease | `REVOKING` | `REVOKED` | Successful manual/security revocation and cleanup |
| Lease | `REVOKING` | `EXPIRED` | Successful TTL-triggered revocation and cleanup |
| Lease | `REVOKING` | `REVOKING` | Retry while cleanup remains unconfirmed |

A request has at most one lease. A failed or lost issuance requires a new request after cleanup; do not unconsume approval. A lease becomes terminal only when target-side absence/cleanup is confirmed. Store `access_disabled_at` separately from `role_dropped_at` so blocked cleanup does not conceal whether access has actually stopped.

### 2.3 Establish least-privilege target provisioning

Use an operator-installed, versioned target bootstrap script. Separate the target data owner, approved `NOLOGIN` access profiles, private broker registry, helper owner, provisioner login, and reaper login.

For version 1, create a vetted read-only profile for explicitly approved objects. Grant the needed database `CONNECT`, schema `USAGE`, and `SELECT`; handle future tables only through owner-specific default privileges or explicit registration. Do not grant access to every future object automatically. Review inherited `PUBLIC` privileges, writable schemas, callable side-effecting functions, and cross-database connections.

Runtime logins must not be database superusers. Implement narrowly scoped, reviewed `SECURITY DEFINER` helpers for provisioning, disabling, terminating, and cleanup. Their owner needs the exact tested capabilities to manage broker roles; it is a privileged trust root and must not be assumable by runtime or ephemeral users. Fix a safe search path, qualify objects, revoke default `PUBLIC EXECUTE`, and validate every argument. PostgreSQL documents these requirements for definer functions. [PostgreSQL CREATE FUNCTION](https://www.postgresql.org/docs/current/sql-createfunction.html)

Helpers must:

- Accept a lease UUID, approved profile/scope, deadline, and credential material—not arbitrary SQL, a caller-selected role name, or an arbitrary PID.
- Derive a short opaque role name such as `esh_<uuidhex>` within PostgreSQL's identifier limit; avoid embedding personal email addresses.
- Register the exact lease/role/OID relationship in a protected target registry. A role-name prefix alone is not sufficient deletion authority.
- Create only `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS` users with bounded connections and no object ownership or grant option.
- Reject duplicate lease creation with conflicting parameters, expired deadlines, unknown profiles, and attempts to manage unrelated roles.
- Prevent provisioner/reaper callers from exploiting search-path substitution, arbitrary membership, cross-tenant role names, or role replacement.

If these capabilities cannot be safely installed on the actual target, report that target as unsupported until its permission model is resolved. Never silently fall back to a stored `postgres` superuser password.

### 2.4 Implement typed target operations

Define a domain `TargetAdapter` protocol with operations for `healthcheck`, `provision`, `disable_login`, `terminate_sessions`, `drop_role`, `inspect_lease`, and `list_managed_leases`. Return typed, secret-redacted results and classify retryable versus permanent failures.

Provisioning must generate passwords with at least 32 random bytes from `secrets`, set native `VALID UNTIL`, and use SCRAM password authentication over verified TLS. Where practical, pass a driver-supported SCRAM verifier rather than plaintext in DDL, and redact both. Bound stored deadline differences using clock checks.

Restrict ephemeral identities in `pg_hba.conf` to the intended database/network and SCRAM authentication; do not permit trust, certificate-only, or other expiry-bypassing authentication for those database roles. Test rule ordering. API mTLS and target database authentication are different controls. [PostgreSQL authentication rules](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)

### 2.5 Implement issuance as a recoverable workflow

1. Authenticate and authorize through application interfaces; tests may inject a typed identity, but do not introduce a deployable authentication bypass.
2. Require an idempotency key. Validate scope, reason length, quota, requested TTL, approval status, and enabled resource state.
3. In one control transaction, reserve quota, store the immutable request/configuration snapshot, allocate the lease/role, persist its deadline, append a provisional audit event, and create recovery work.
4. Commit before contacting the target.
5. Provision on the target with bounded timeouts and per-lease target serialization. Registration and role creation must be atomic on the target.
6. In a new control transaction, verify the current request/claim state and deadline. Mark active and append the issuance event only if still valid.
7. Return the password only after that transaction commits. Set `Cache-Control: no-store`; disable response-body logging at every layer.
8. If anything is uncertain, schedule compensation/reconciliation. Never claim cross-database atomicity.

Do not persist plaintext or reversibly encrypted lease passwords in version 1. An identical retry returns the existing request/lease status without credentials; it must not create a second role. A changed request using the same key returns a conflict. If the original credential response is lost, revoke that lease and request a new one. Explain this behavior in the CLI.

### 2.6 Implement safe revocation and recovery

Revoke in this order:

1. Persist the revocation intent and audit event when the control database is available.
2. Commit `NOLOGIN` and password invalidation on the target before session cleanup.
3. Terminate sessions whose authenticated role/OID matches the protected registry entry. Recheck until none remain; include a reconnect race test.
4. Remove broker-owned grants/membership and drop the role. Verify absence.
5. Record completion, cause, timings, and cleanup result.

Do not use blanket `DROP OWNED ... CASCADE` on existing targets. Unexpected dependencies leave the role disabled, trigger an alert, and require scoped cleanup. PostgreSQL role deletion can be blocked by object ownership or grants. [PostgreSQL DROP ROLE](https://www.postgresql.org/docs/current/sql-droprole.html)

Use database-backed claims with expiry and fencing counters for concurrent workers. Target helpers must serialize operations for the same lease and retain revocation tombstones so a delayed provision call cannot recreate a revoked role. Reconciliation compares control records, target registry, and actual target roles in both directions. Confirm uncertain commits by inspection; never blindly retry role creation with a new username.

**Phase 2 completion gate:** Against real disposable PostgreSQL, issue a lease, connect, read only approved data, fail write/escalation attempts, revoke, terminate a running query, and prove reconnect fails. Test concurrent duplicate requests, crashes after target commit, retries after disable/drop, deadline changes, and dependency failures. No secret appears in persisted control data or captured logs. Adapter tests must pass using the real limited runtime identities.

**LLM instruction:** “Implement Phase 2 only using real PostgreSQL integration tests. Build migrations, permissions, typed target adapter, state transitions, idempotency, and compensation before adding HTTP routes. Do not substitute Redis TTL for durable leases or use a superuser at runtime.”

## Phase 3 — Build identity, policy, approvals, API, and CLI

### 3.1 Implement mTLS identity and enrollment

1. Build an explicit development CA/certificate generator. Store local private keys outside Git. The production CA private key must not be shipped in the API image or hosted by the broker.
2. Document administrator-verified enrollment from a user-generated CSR. Use short-lived client certificates, unique serials, client-auth usage, and stable identity mapping; implement renewal, rotation, and loss/revocation procedures.
3. Configure Nginx to verify the client certificate chain, validity, and configured revocation list. Overwrite client-supplied identity headers with proxy-generated verified certificate metadata.
4. Allow only the trusted proxy to reach the API; publish no direct API port. The API resolves trusted issuer/serial to an active certificate and principal in PostgreSQL for every protected request. Reject revoked/unregistered certificates even on reused TLS connections.
5. Validate server certificates in the CLI; do not add a production `--insecure` option. Use TLS hostname verification for API, control database, and target connections as appropriate to their network boundaries.
6. Disabling a principal must deny new requests and enqueue revocation of all their active/provisioning leases. Certificate revocation follows the same conservative lease-revocation rule in version 1.

### 3.2 Implement deterministic authorization

Start with RBAC plus explicit resource/TTL/approval conditions, not a custom general-purpose policy language. Policy input is authenticated principal and groups, target, privilege profile, requested TTL, reason, approval, and current state.

Default deny. Never accept groups or identity from request JSON. Deny requests exceeding the selected policy and resource maximum; return the allowed bound instead of silently increasing access. Default omitted TTL to the configured default capped by the permitted maximum. Bound concurrent leases per principal/target and rate-limit issuance atomically.

Use explicit policy IDs internally. If multiple eligible policies match, select deterministically using a documented conservative rule; reject conflicting policies at import where possible. Persist the selected policy version and decision inputs. Re-evaluate authorization when approved requests are issued. Resource/policy disablement must cancel pending requests and schedule revocation of affected leases in version 1.

When approval is required, capture an independent reviewer's identity, target/scope/TTL, decision time, and a short approval deadline. Prevent self-approval. Consume approval once. A ticket string is justification, not evidence that an external ticketing system approved the request.

### 3.3 Implement the REST contract

| Endpoint | Behavior |
|---|---|
| `GET /health/live` | Process liveness; minimal output |
| `GET /health/ready` | Control database and required configuration ready; report issuance readiness separately |
| `GET /v1/resources` | Only resources visible to the caller |
| `POST /v1/access-requests` | Create an authorized request; idempotent; immediate or approval-pending |
| `GET /v1/access-requests/{id}` | Owner or authorized reviewer sees status; no secret |
| `POST /v1/access-requests/{id}/decision` | Authorized independent reviewer approves or denies |
| `POST /v1/access-requests/{id}/issue` | Requester consumes approved request and receives credentials once |
| `GET /v1/leases` | Paginated caller-visible metadata; no passwords |
| `GET /v1/leases/{id}` | Owner/operator metadata only |
| `POST /v1/leases/{id}/revoke` | Owner or revocation operator schedules idempotent revocation |
| `GET /v1/audit/events` | Restricted, paginated auditor access; sanitized fields |

Use `201` for newly created requests/issued resources, `202` for asynchronous revocation, `401` for missing/invalid application identity where TLS did not already reject it, `403` for prohibited actions, `404` for inaccessible objects, `409` for conflicting replay/state, `422` for invalid input, `429` for quotas/rate limits, and `503` when safe issuance is unavailable.

Document OpenAPI schemas, pagination, request IDs, structured error codes, retry rules, timeout behavior, `Idempotency-Key`, and secret response handling. Protect production API documentation. Resource registration and identity/policy administration remain operator CLI actions, so public requests cannot supply arbitrary hosts or secret paths.

### 3.4 Build the CLI workflows

Implement these commands and document their exact behavior:

```bash
shieldctl configure --endpoint https://broker.example.internal
shieldctl whoami
shieldctl resources list
shieldctl request --resource target-db --ttl 30m --reason "INC-402 debugging"
shieldctl requests show <request-id>
shieldctl requests approve <request-id>
shieldctl connect --request <approved-request-id>
shieldctl connect --resource target-db --reason "INC-402 debugging"
shieldctl leases list
shieldctl leases revoke <lease-id>
shield-admin resources validate <manifest-path>
shield-admin resources apply <manifest-path>
shield-admin policies apply <manifest-path>
shield-admin principals disable <principal-id>
shield-admin audit verify
```

`request` creates/returns request metadata; `connect` performs one-time issuance and starts `psql`. Immediate requests become approved automatically if policy permits. A standalone credential-output mode must require an explicit `--output json --show-secret`; normal output never prints a password or secret-bearing URI.

Keep credentials in process memory by default. Start `psql` with a child-only environment and argument-array execution; never `shell=True`, a password argument, a shell `export`, or a copied `.env` file. A child environment avoids routine shell-history leakage but remains visible to sufficiently privileged local processes; do not describe it as immunity from laptop compromise. Remove references after use without promising reliable zeroization of immutable Python strings.

On normal child exit or Ctrl+C, request lease revocation in `finally`; worker expiry remains responsible if the CLI is killed. Use safe config/key permissions, including Windows ACL guidance, deterministic exit codes, timeouts, and server-time expiry display. Never automatically reissue after an ambiguous credential response.

**Phase 3 completion gate:** Run the entire workflow through real TLS. Reject missing/untrusted/expired/revoked certificates, spoofed identity headers, direct API access, self-approval, unauthorized resource access, cross-user lease lookup/revocation, and request replay. Demonstrate both immediate and approved access using `psql`. Disabling a user triggers revocation of existing leases.

**LLM instruction:** “Implement Phase 3 only. Preserve domain/application separation, use the real mTLS edge in end-to-end tests, and build both immediate and approval-required CLI flows. Do not expose administrative target registration to normal users or log credential responses.”

## Phase 4 — Finish revocation reliability, audit integrity, and operational validation

### 4.1 Run a durable worker independently of FastAPI

Deploy `python -m ephemeralshield.worker.main` separately. Do not use FastAPI startup tasks, in-memory timers, or request background tasks as the sole reaper.

Implement a one-second indexed PostgreSQL scan for due leases and pending revocations, bounded batches, durable claims, retry backoff with jitter, per-target concurrency limits, worker heartbeats, graceful shutdown, and startup reconciliation. Multiple workers must safely process work without concurrent conflicting DDL.

Retain nonterminal work until resolved. A failed revocation remains visible and continues retrying with alerts; it must not disappear into a dead-letter queue with no recovery owner. A disabled resource still needs cleanup connectivity and secret access for its old leases. Preserve the original target configuration version for cleanup after configuration changes.

Redis may nudge the worker sooner or accelerate reads. Missed hints, flushed Redis state, and reconnects must not affect eventual cleanup. Redis never stores passwords, and cached policy grants must not override current disabled identity/resource state.

When the control database is unavailable, deny new issuance. Use the protected target registry and its deadlines for narrowly scoped emergency expiry where the worker can still reach the target. Resume control-plane reconciliation when connectivity returns. Do not claim atomic audit logging during an unavailable audit store; record the target cleanup receipt and reconciliation gap explicitly. If both control and target are unreachable, alert and report revocation as unconfirmed.

### 4.2 Make the audit chain deterministic and concurrency-safe

Specify a versioned canonical event format: UTF-8 encoding, deterministic key ordering, fixed UTC timestamp representation, unambiguous field framing, no floating-point ambiguity, and explicit null handling. Store the canonical bytes being hashed, not only a JSONB rendering.

Each event contains sequence, timestamp, action, actor, nullable request/lease ID, request correlation ID, decision/resource/policy version, result, sanitized metadata, and previous hash. Hash the complete envelope with a domain/version prefix. No raw SQL passwords, authentication material, free-form stack traces, or uncontrolled credential responses.

Serialize append operations by locking `audit_chain_head`. Allocate the next sequence and insert/update the head in the same transaction. Do not assume `BIGSERIAL` values are contiguous or that concurrent inserts complete in sequence order. Commit lease state changes and their corresponding ledger events together.

Give runtime identities append-only access through a restricted append interface; no update/delete or chain-head rewriting. Implement `shield-admin audit verify` to check canonical encoding, sequence continuity, all hashes, genesis, expected head, and signed external checkpoints.

Export checkpoints at least once per minute to independently administered append-only storage: ledger ID, sequence, head hash, checkpoint time, key ID, and Ed25519 signature. Retain trusted public keys and their rotation history. Test verification against the latest externally retained checkpoint; an old valid checkpoint alone cannot expose a deleted later tail. Document the unanchored interval and alert on checkpoint lag.

### 4.3 Distinguish lease history from observed sessions

Collect target connection/disconnection logs keyed by generated username and timestamp, and correlate them to lease IDs. Treat client-controlled application names as supplemental metadata. Record observed session start/end when available; lease duration is not session duration, and a lease can have multiple sessions.

If query auditing is enabled, document which statements/objects it covers, storage access, retention, overhead, and possible PII exposure. Version 1 must never answer “which records were read” solely from broker issuance events.

### 4.4 Add actionable telemetry and runbooks

Expose bounded-label metrics for issuance latency/results, active leases, oldest overdue lease, time to disable access, time to terminate sessions, cleanup backlog, retry count, last successful scan, worker heartbeat age, target failures, clock skew, audit verification failures, and checkpoint age. Keep usernames, emails, reasons, and lease IDs out of metric labels.

Emit structured redacted logs with request/lease correlation IDs. Alert when no worker is healthy, expiry exceeds the tested threshold, role cleanup is blocked, a target is unreachable, an orphan appears, certificates approach expiry, or audit/checkpoint validation fails. Stop new issuance when reaper heartbeat is stale beyond the configured threshold; revocation paths remain available.

Write runbooks for target outage, control database outage, Redis outage, lost certificates, stolen broker machine credentials, orphan users, audit tampering, clock drift, and emergency suspension of issuance.

### 4.5 Prove the failure behavior

| Test | Required result |
|---|---|
| Redis unavailable or expiration message lost | PostgreSQL scanning still revokes; no dependency on Redis recovery |
| API killed after target commit | Reconciliation finds the role and revokes uncertain issuance |
| Reaper killed mid-operation | Another/restarted worker resumes idempotently |
| Two workers claim the same lease | No double issuance or unsafe conflicting cleanup |
| Delayed provision after revocation | Fencing/tombstone prevents resurrection |
| Long-running query and idle transaction at expiry | Sessions terminate and open transactions roll back |
| Rapid reconnect during cleanup | Login disabled first; no surviving authenticated session |
| Target unreachable | No false success; bounded retries, alerts, reconciliation on recovery |
| Control database unavailable | New issuance denied; supported target-registry expiry continues; audit gap surfaced |
| Native password expiry with worker stopped | New SCRAM logins fail; document that existing sessions can remain |
| Role dependency blocks drop | Access disabled, cleanup state nonterminal, no destructive cascade |
| Role missing before cleanup | Idempotent success after registry/state verification |
| User disabled or certificate revoked | New requests denied; existing leases enter revocation |
| Ephemeral user alters own password/settings | Deadline and permission boundaries still enforced; test actual role capabilities |
| Ledger row edit/deletion/reorder | Verification fails |
| Ledger tail deletion or full rewrite | External checkpoint comparison detects mismatch where anchored |
| Secret-bearing exception/HTTP/DDL paths | No plaintext password or verifier in collected logs/traces |
| Restored old control backup | Reconcile target reality; never resurrect terminal/expired access |
| Clock skew | Detected; issuance fails safely above the configured threshold |

Use unit tests with injected clocks for state/TTL logic, real PostgreSQL for privilege/session behavior, and controllable network failures for resilience tests. Do not replace these with SQLite or only mocks. Use bounded polling instead of arbitrary long sleeps; a small real-time expiry test is still required.

Add a repeatable load profile, initially 100 active leases with 20 expiring together. Record environment, throughput, p50/p95/p99 revocation latency, and worst observed overdue time. Increase the documented supported load only after measuring it. Require coverage of every security state transition; use at least 90% branch coverage for domain/application code as a supporting gate, not a substitute for behavior tests.

**Phase 4 completion gate:** All resilience/security tests pass, the declared load meets the expiry-latency target, audit verification detects anchored tampering, telemetry identifies failed revocation, and documented failure limits match observed behavior. Commit sanitized test evidence and the operational runbooks.

**LLM instruction:** “Implement Phase 4 only. Test failures against real PostgreSQL and independent worker processes. Treat unconfirmed revocation as an active incident, validate the externally anchored audit chain, and document actual guarantees rather than claiming exact destruction during outages.”

## Phase 5 — Package, deploy privately, and publish a usable GitHub release

### 5.1 Build reproducible release artifacts

1. Build a Python wheel with `shieldctl` and `shield-admin` console entry points. Validate installation in a fresh virtual environment without the repository on the import path.
2. Build a multi-stage container with the same compatible Python ABI and OS library family in build/runtime stages. Use locked dependencies and pin the base digest. Do not copy Python 3.12 packages into an unrelated distroless Python interpreter.
3. Run as a fixed non-root UID with a read-only root filesystem, a small temporary filesystem, dropped Linux capabilities, `no-new-privileges`, and resource limits. Exclude certificates, `.env`, dumps, Git metadata, and test credentials from the build context.
4. Use the same application image with separate API and worker commands. Include no development dependencies in runtime.
5. Generate an SBOM, scan packages/image, record checksums, and attach provenance/signatures to releases. Block high/critical findings unless a narrowly scoped, time-limited exception is documented and reviewed.

### 5.2 Create GitHub CI and release workflows

Create separate workflows for PR verification, release publishing, and controlled deployment:

| Workflow | Required stages |
|---|---|
| `ci.yml` | Frozen install; Ruff format/check; mypy strict; architecture import rules; unit/contract/integration/security tests; migrations from empty and prior release |
| `security.yml` | Secret scan, Bandit, dependency audit, container scan; scheduled repeat scans |
| `resilience.yml` | Real API/worker/target fault tests and bounded expiry timing tests; required for release |
| `release.yml` | Protected version tag; all release gates; build wheel/image; SBOM/provenance; push GHCR; create GitHub release |
| `deploy.yml` | Protected environment; exact approved image digest; preflight, backup, migration, rollout, smoke tests, rollback path |

Pin third-party Actions to full commit SHAs, use minimal token permissions, and avoid running untrusted pull-request code with deployment credentials. Never expose a private self-hosted runner to arbitrary fork code. Prefer short-lived deployment identity; use a dedicated constrained deploy key only when the chosen host lacks workload identity. [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)

Use disposable control and target databases in CI with synthetic data. Publish image tags for semantic version and commit SHA; deploy by digest, never by mutable `latest`. Publish only after required checks pass. [GitHub image publishing](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

### 5.3 Deploy one concrete supported topology

Version 1 deployment target: a private Linux VM running Docker Compose, with Nginx, API, two worker instances, control PostgreSQL, optional Redis, monitoring, and encrypted persistent backups. Declare that the single VM/control database remains a failure domain; two workers are process redundancy, not host-level high availability.

Network paths:

- Authorized clients reach Nginx HTTPS through the private network/VPN.
- Nginx reaches the unexposed API on a private container network.
- API/workers reach control PostgreSQL and registered target management endpoints.
- Approved clients reach the target SQL endpoint through the permitted private network using their ephemeral credentials.
- Metrics are reachable only by monitoring.

Direct client SQL access is necessary in this credential-broker design. A policy allowing only broker/reaper traffic to the target would prevent developers from using their credentials. Configure client and management networks separately; a proxy-only network design belongs to a future proxy release.

Never publicly expose PostgreSQL, Redis, API internals, metrics, or an unauthenticated issuance demo. Keep target management secret material in a secret manager or protected mounted secret files; store references in the database. Compose secret mounts do not independently provide an encrypted secret-management service.

Execute deployment in this order:

1. Prepare the patched host, private DNS, firewall, time synchronization, storage, and backup destination.
2. Obtain server/client trust material and install restricted secret files; keep production CA signing keys elsewhere.
3. Validate the target and review/install the scoped bootstrap using a separate operator identity.
4. Start control PostgreSQL and optional Redis; take an initial backup.
5. Run Alembic through a one-shot migration job with a dedicated migration identity.
6. Start workers and verify fresh heartbeats, successful scans, target access, and clock checks.
7. Start API/Nginx and monitoring; import validated resource/group/policy manifests and enroll a test identity.
8. Run issuance, approved read, denied write, manual revoke, expiry, certificate rejection, and audit/checkpoint smoke tests with synthetic data.
9. Enable normal issuance only after all smoke tests and alerts are verified.
10. Record image digest, schema version, configuration versions, tested PostgreSQL versions, deployment date, and measured limits.

### 5.4 Implement backup, upgrade, and recovery procedures

Back up control-plane data, audit events/checkpoints, protected target registry metadata, configuration, and required secret-recovery material under separate access controls. Define and test initial recovery objectives; use a daily backup plus WAL archiving if targeting an RPO of 15 minutes and an RTO of one hour. Publish those objectives only after a restore drill supports them.

For upgrades, pause issuance, keep revocation running, back up, apply backward-compatible expand migrations, roll out the pinned image, verify worker/target health, and resume issuance. Perform destructive schema contraction in a later release. Never rely on an automatic down-migration to reverse a security-critical deployment.

For rollback, restore the previous compatible image/configuration, preserve revocation, and verify schema compatibility. For disaster recovery, start with issuance disabled, compare target registries and live roles to restored control data, disable overdue/unknown broker-managed access safely, verify audit checkpoints, then resume issuance. Do not recover or re-deliver old lease passwords.

### 5.5 Make the GitHub repository usable by another engineer

Create a repository named `ephemeralshield`, choose a deliberate open-source license (Apache-2.0 is a reasonable default), and populate these documents before the first release:

- `README.md`: problem, five-minute synthetic quickstart, architecture, supported versions, CLI examples, security guarantees and failure limits, cleanup instructions, and troubleshooting.
- `docs/architecture.md`: trust boundaries, data model, state transitions, target/control transaction boundaries, recovery behavior, and direct SQL client path.
- `docs/permissions.md`: exact runtime/bootstrap capabilities, role grants, target helper ownership, and verification queries.
- `docs/configuration.md`: all settings with defaults, units, secret references, and development/production differences.
- `docs/api.md`: generated OpenAPI plus one-time credential/idempotency semantics.
- `docs/runbooks/`: installation, enrollment, revocation, outages, backups, restores, upgrades, and incident response.
- `SECURITY.md`: private vulnerability-reporting process, supported releases, threat-model limits, and secrets handling.
- `CONTRIBUTING.md`: setup, coding boundaries, migration rules, test commands, and review requirements.
- `CHANGELOG.md`, PR/issue templates, CODEOWNERS, and example resource/policy manifests containing no real credentials or endpoints.
- `docs/evidence/`: sanitized test summaries, latency measurements, restore drill, and audit verification examples; no raw customer data or secrets.

Enable branch protection, required status checks, dependency alerts/updates, and available secret protection. Scan the entire Git history and release artifacts before making the repository public. Add accurate topics such as `python`, `fastapi`, `postgresql`, `zero-trust`, `jit-access`, and `security`.

Create release `v0.1.0` with wheel, checksums, SBOM, image digest, release notes, supported target versions, installation steps, and limitations. Publish an authenticated synthetic demonstration recording if desired; public demo data must not connect to a real production target. A GitHub release is sufficient distribution for version 1; PyPI publication is a separate later decision.

### 5.6 Final acceptance checklist

- A new user can clone the repository and run the documented synthetic demo without guessing configuration.
- Your real local `target-db` can be registered through the documented, non-destructive bootstrap path.
- Authentication, authorization, approvals, TTL enforcement, and cross-user isolation pass real end-to-end tests.
- Every successful issuance has durable state and audit evidence before the password is returned.
- Expired credentials reject new connections, and sessions are terminated within the measured healthy-condition target.
- Lost notifications, worker restarts, ambiguous target commits, and restore reconciliation have passing tests.
- Revocation failures remain visible until resolved; no unsafe cleanup of unrelated roles or data occurs.
- Audit verification checks independently retained checkpoints and reports evidence gaps honestly.
- No secret is present in Git, images, CI logs, API logs, audit payloads, or release artifacts.
- Backup restoration, upgrade, rollback, secret rotation, and certificate revocation have been exercised.
- The private deployment passes smoke tests, and the released wheel/image match the documented source tag.
- GitHub documentation explicitly distinguishes a production-oriented release from an externally audited security product.

**Phase 5 completion gate:** A fresh-machine quickstart and the private deployment both work; restore/rollback drills pass; CI is green; `v0.1.0` artifacts and documentation are available through GitHub. Report deployment or publication as blocked if credentials/access are absent—never invent URLs, successful runs, or release evidence.

**LLM instruction:** “Implement Phase 5 only. Build and verify release artifacts, CI, private Compose deployment, and operator documentation. Use the tested image digest and preserve revocation during migrations. Publish/deploy only within the access and authorization provided; if external access is missing, complete the reviewable artifacts and state the exact blocker.”

### Reusable LLM execution contract

Put this instruction in `AGENTS.md` and use it at the start of every phase:

> Read AGENTS.md, docs/development-plan.md, docs/progress.md, applicable ADRs, and the relevant existing code before making changes. Implement the requested phase in its documented order. Preserve the dependency boundaries, security invariants, and existing user changes. Do not invent unavailable credentials, services, successful tests, or deployment results. Use real PostgreSQL for permissions and session behavior. Never weaken an acceptance test or security control merely to make a build pass. Record necessary design changes in an ADR before implementing them. After each coherent task, run the relevant checks and update docs/progress.md with files changed, migrations, exact commands/results, evidence paths, blockers, and the next task. Mark a phase complete only when its completion gate passes. If instructed to execute the entire plan, proceed automatically to the next phase after its gate passes; do not repeatedly ask for approval for routine reversible work.

Track each task as `not started`, `in progress`, `blocked`, or `verified`. Start each phase with a branch such as `phase/1-foundation` and end with a reviewable PR. Acceptance evidence belongs in the repository so another LLM can continue without relying on chat history.
