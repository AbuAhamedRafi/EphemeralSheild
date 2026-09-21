## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Infrastructure/tooling change

## Checklist

- [ ] Tests pass: `uv run pytest tests/unit/ -v`
- [ ] Lint passes: `uv run ruff check src/ tests/`
- [ ] Type check passes: `uv run mypy src/`
- [ ] No secrets in diff (checked by pre-commit hook)
- [ ] Documentation updated if behavior changed
- [ ] ADR written if security-sensitive decision was made
- [ ] Migration tested from clean database (if applicable)

## Security Considerations

Describe any security implications of this change, or write "None" if not applicable.
