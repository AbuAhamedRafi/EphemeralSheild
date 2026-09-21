"""
EphemeralShield — Background Worker.

This package contains the dedicated asyncio worker process that handles:
  - Lease expiration scanning (1-second interval)
  - Credential revocation execution
  - Target reconciliation
  - Work item processing with durable claims

The worker runs as a SEPARATE process from the API (§4.1):
  python -m ephemeralshield.worker.main

WHY a separate process?
  - API process restart doesn't interrupt revocation
  - Worker can be scaled independently
  - Crash isolation — a worker bug doesn't take down the API
  - Different resource requirements (CPU-bound cleanup vs I/O-bound API)
"""
