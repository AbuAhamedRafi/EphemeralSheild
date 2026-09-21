# Security Policy

## Reporting Vulnerabilities

**DO NOT** report security vulnerabilities through public GitHub issues.

Please report vulnerabilities privately through GitHub's security advisory feature:
1. Go to the **Security** tab of this repository
2. Click **Report a vulnerability**
3. Provide a clear description, reproduction steps, and impact assessment

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current |

## Security Claims

EphemeralShield makes the following security claims. Each has been validated through the test suite documented in `docs/evidence/`.

### What We Provide

1. **No standing human database credentials.** A protected machine identity provisions and revokes ephemeral users. Its ownership, rotation, and emergency recovery are documented in `docs/permissions.md`.

2. **Password expiry is not session termination.** We use `VALID UNTIL` for native expiry AND actively terminate sessions. PostgreSQL's `VALID UNTIL` only prevents new logins — it does not close existing connections.

3. **Revocation has a measured latency.** Target: p99 session termination within 5 seconds of expiry under documented load. This is a measured target, not an unconditional guarantee.

4. **PostgreSQL is authoritative.** Redis is an optional optimization. The system functions correctly if Redis is completely unavailable.

5. **Tamper-evident audit chain.** Each audit event is hash-chained. Signed checkpoints are exported to independent storage. An attacker who can replace the entire ledger can recompute an unanchored chain — hence the external checkpoints.

### What We Do NOT Provide

6. **Issuance evidence is not query evidence.** A lease record proves authorization. It does NOT prove which specific records were read. Use PostgreSQL's `pgaudit` extension for query-level auditing.

7. **Compliance is not automatic.** We describe supported controls and evidence. We do NOT claim SOC 2, ISO 27001, or HIPAA certification.

8. **Read replicas are not supported in v1.** Physical standbys cannot execute provisioning DDL.

## Secrets Handling

- Secrets are NEVER stored in Git history, Docker images, CI logs, API logs, audit payloads, or release artifacts
- Runtime secrets use `SecretStr` (Pydantic) which redacts values in repr/str/logs
- The `.env` file and `secrets/` directory are gitignored
- Docker images exclude secrets via `.dockerignore`
- Pre-commit hooks scan for accidentally committed secrets

## Threat Model

See `docs/threat-model.md` for the complete threat model.
