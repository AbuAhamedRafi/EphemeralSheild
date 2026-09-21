"""
EphemeralShield — Application Layer (Use Cases).

This package contains the orchestration logic: issue credentials, approve
requests, revoke leases, reconcile state, and manage audit records.

Dependency rules (§1.4):
  - MAY import from: ephemeralshield.domain
  - MAY depend on: typed port interfaces (protocols)
  - MUST NOT import from: infrastructure, api, worker, cli
  - MUST NOT directly use SQLAlchemy, FastAPI, or any framework
"""
