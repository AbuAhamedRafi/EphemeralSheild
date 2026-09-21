# Threat Model

## Scope

This threat model covers EphemeralShield v0.1.x — a PostgreSQL credential broker deployed on a private network with mTLS authentication.

## Assets

| Asset | Sensitivity | Location |
|---|---|---|
| Target database content | HIGH — customer PII, financial data | Target PostgreSQL |
| Ephemeral credentials (passwords) | HIGH — grant database access | In-memory only (never persisted) |
| Audit chain (ledger) | HIGH — evidence integrity | broker-db + external checkpoints |
| Broker machine identity (provisioner/reaper keys) | CRITICAL — can create/drop roles | Secret files, mounted at runtime |
| mTLS CA private key | CRITICAL — can mint identities | NOT in broker, stored separately |
| Client certificates | MEDIUM — authentication tokens | Developer machines |
| Broker configuration | MEDIUM — contains secret references | .env (never committed) |

## Threat Categories

### T1: Credential Theft

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Password leaked in logs | SecretStr redaction, no response body logging | Developer console on client machine |
| Password stolen from API response | One-time delivery, Cache-Control: no-store | Network MITM if mTLS is misconfigured |
| Password remains in Python memory | Explicit deletion (best effort — Python strings are immutable) | OS-level memory inspection |

### T2: Unauthorized Access

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Direct API access bypassing mTLS | Nginx drops non-mTLS connections, API unreachable from public | Misconfigured firewall |
| Forged identity headers | Proxy overwrites client headers, API rejects direct connections | Proxy compromise |
| Expired certificate reuse | Certificate validity check on every request | Clock skew between proxy and CA |

### T3: Privilege Escalation

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Ephemeral user elevates to superuser | NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION | Unpatched PostgreSQL CVE |
| Ephemeral user modifies data | Read-only profile (SELECT only) | Callable functions with side effects |
| Ephemeral user alters own password | VALID UNTIL still enforced, worker checks regularly | Extended access until next scan |

### T4: Revocation Failure

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Worker crash during revocation | Durable work claims, another worker resumes | All workers down simultaneously |
| Target unreachable during revocation | Bounded retries, alerts, NOLOGIN as first step | Extended session during outage |
| Race: reconnect after NOLOGIN | Terminate sessions after NOLOGIN, recheck | Sub-second race window |

### T5: Audit Tampering

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Direct ledger modification | Hash chain detects breaks | Attacker rewrites entire chain |
| Full chain rewrite | External signed checkpoints | Checkpoint storage compromise |
| Audit gap during outage | Explicit gap recording, reconciliation on recovery | Lost events during double failure |

### T6: Supply Chain

| Threat | Mitigation | Residual Risk |
|---|---|---|
| Compromised dependency | pip-audit, Dependabot, lockfile | Zero-day before advisory |
| Compromised Docker base image | Pinned digests, Trivy scanning | Image registry compromise |
| Compromised CI action | SHA-pinned actions, minimal permissions | GitHub platform compromise |

## Assumptions

1. Docker host is patched and not compromised
2. Network between containers is private (Docker bridge)
3. Time is synchronized (NTP) within acceptable skew
4. The mTLS CA is operated securely and separately from the broker
5. Developers' machines are not pre-compromised when using credentials
