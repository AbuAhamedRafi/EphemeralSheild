# Contributing to EphemeralShield

## Development Setup

### Prerequisites
- Docker Desktop
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### First-Time Setup

```powershell
# Install dependencies
uv sync

# Generate local secrets (.env and signing keys)
powershell -File scripts/generate-secrets.ps1

# Start Docker services
docker compose -f deploy/compose.dev.yaml up -d --build --wait

# Run migrations
uv run alembic upgrade head

# Install pre-commit hooks
uv run pre-commit install

# Verify everything works
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/unit/ -v
```

## Coding Standards

### Dependency Direction (STRICT)

```
domain → (nothing — pure Python)
application → domain + typed ports
infrastructure → implements ports
api/worker/cli → application use cases
bootstrap.py → wires everything together
```

Enforced by `import-linter` in CI. If you import SQLAlchemy in a domain module, CI will fail.

### Type Safety
- All code must pass `mypy --strict`
- No `Any` types, no `# type: ignore` without a documented reason
- Use `Mapped[]` and `mapped_column()` for SQLAlchemy models

### SQL Safety
- Use parameter binding for all values: `text("SELECT * FROM t WHERE id = :id").bindparams(id=value)`
- Use `psycopg.sql` composition for identifiers (table/column names)
- NEVER use f-strings or `.format()` for SQL construction

### Migrations
- All schema changes go through Alembic — no `create_all()` in production
- Review every migration manually before committing
- Test migrations from empty AND from the previous release

### Security
- No secrets in code, logs, tests, or Git history
- Use `SecretStr` for any sensitive configuration
- No `shell=True` in subprocess calls
- No `--insecure` or TLS verification bypass in production code

## Pull Request Checklist

- [ ] Tests pass: `uv run pytest tests/unit/ -v`
- [ ] Linter passes: `uv run ruff check src/ tests/`
- [ ] Type check passes: `uv run mypy src/`
- [ ] No secrets in diff
- [ ] Migrations tested from clean database
- [ ] Documentation updated if API/behavior changed
- [ ] ADR written if security-sensitive decision was made
