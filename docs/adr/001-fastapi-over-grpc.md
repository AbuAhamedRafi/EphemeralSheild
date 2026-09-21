# ADR-001: FastAPI over gRPC for Version 1

## Status: Accepted

## Context

The original project concept considered using gRPC for the API transport. We needed to decide between:
1. **gRPC** — Binary protocol, code generation, HTTP/2
2. **FastAPI (REST/JSON)** — Standard HTTP API with OpenAPI
3. **Both** — Dual transport

## Decision

**Use FastAPI with REST/JSON for version 1. Do not implement gRPC.**

## Rationale

1. **Single transport simplicity.** Maintaining two transports (gRPC + REST) doubles the API surface area, testing burden, and documentation effort. For a v0.1 release, one well-tested transport is better than two partially-tested ones.

2. **FastAPI fits the workload.** This project is an asynchronous API + background worker + CLI. FastAPI supports async natively, has automatic OpenAPI generation, and integrates cleanly with Pydantic for validation.

3. **CLI compatibility.** The `shieldctl` CLI uses HTTPX to communicate with the API. HTTP/JSON is universally supported. gRPC requires generated stubs and a heavier client dependency.

4. **Async I/O support.** FastAPI + Uvicorn handle the concurrent database operations (broker-db + target-db) needed for credential issuance without blocking.

5. **gRPC is not lost.** If v2 needs binary efficiency or streaming (e.g., audit event streaming), gRPC can be added alongside REST. The application layer is transport-agnostic by design.

## Consequences

- All API endpoints use REST/JSON over HTTPS
- OpenAPI documentation is auto-generated
- No `.proto` files or code generation toolchain needed
- Performance-sensitive v2 features may require reconsidering gRPC
