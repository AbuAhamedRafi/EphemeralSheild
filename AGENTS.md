# AGENTS.md — LLM Execution Contract

> Read this file, `docs/development-plan.md`, `docs/progress.md`, applicable ADRs, and the relevant existing code before making changes. Implement the requested phase in its documented order. Preserve the dependency boundaries, security invariants, and existing user changes. Do not invent unavailable credentials, services, successful tests, or deployment results. Use real PostgreSQL for permissions and session behavior. Never weaken an acceptance test or security control merely to make a build pass. Record necessary design changes in an ADR before implementing them. After each coherent task, run the relevant checks and update `docs/progress.md` with files changed, migrations, exact commands/results, evidence paths, blockers, and the next task. Mark a phase complete only when its completion gate passes. If instructed to execute the entire plan, proceed automatically to the next phase after its gate passes; do not repeatedly ask for approval for routine reversible work.

## Coding Rules

These rules are enforced in CI and apply to all code changes:

### Dependency Direction
- **Domain** has NO framework imports (no SQLAlchemy, FastAPI, Redis, Psycopg)
- **Application** depends on domain and typed ports only
- **Infrastructure** implements ports
- **API/Worker/CLI** call application use cases
- Only the **composition root** (`bootstrap.py`) wires concrete implementations

### Route Rules
API routes ONLY:
1. Authenticate the caller
2. Validate input (Pydantic)
3. Invoke a use case
4. Serialize results

Routes must NOT contain: SQL, DDL, policy decisions, or background reapers.

### Database Rules
- One unit of work per control-plane operation
- Do NOT share async sessions between concurrent tasks
- All schema changes via Alembic migrations — NO production `create_all()`
- Parameter binding for values, safe SQL composition for identifiers
- Never interpolate user input into SQL, shell commands, or connection strings

### Type Safety
- Type ALL application code; run `mypy --strict`
- Avoid `Any`, wildcard imports, unreviewed ignores, and broad exception suppression

### Security Rules
- Secrets must NOT appear in: logs, exception bodies, traces, metrics, audit payloads, test snapshots, or Git history
- Use timezone-aware UTC datetimes everywhere
- Target operations have bounded connection, query, lock, and retry timeouts
- Never hold a control DB transaction open while waiting on target network I/O
- Document security-sensitive decisions in ADRs
- No silent architecture changes, fake passing tests, or TODO implementations on active security paths

### Configuration
- Centralize all configuration in `settings.py`
- No hardcoded hosts, credentials, TTLs, or environment-specific paths
- `.env.example` contains placeholders only

## Phase Tracking
Track each task as: `not started` | `in progress` | `blocked` | `verified`
Start each phase with a branch (e.g., `phase/1-foundation`)
Acceptance evidence belongs in the repository.
