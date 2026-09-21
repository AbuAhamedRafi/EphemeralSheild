# =============================================================================
# EphemeralShield - Multi-Stage Dockerfile
# =============================================================================
# This Dockerfile builds a production-ready container for both the API server
# and the background worker. The SAME image serves both - only the CMD differs.
#
# WHY multi-stage?
#   Stage 1 (builder): Installs all build tools and dependencies.
#   Stage 2 (runtime): Copies only the installed packages - no compilers,
#   no dev dependencies, no source control. This makes the image ~70% smaller
#   and removes attack surface.
#
# WHY Python 3.12-slim?
#   The -slim variant is based on Debian but strips docs, man pages, and
#   rarely-used packages. It's ~50MB vs ~350MB for the full image.
#   We avoid -alpine because psycopg3's C extensions may have build issues
#   with musl libc, and debugging alpine containers is harder.
#
# Security hardening:
#   - Non-root user (uid=1000)
#   - No dev dependencies in runtime
#   - .dockerignore excludes secrets, .env, tests, and .git
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv - the fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files FIRST - this layer is cached unless dependencies change.
COPY pyproject.toml uv.lock ./

# Install external dependencies into virtual environment without local project
# --no-install-project allows caching 3rd-party dependencies before copying source
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and metadata needed to build the project package
COPY README.md .
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini .

# Now install the project package itself
RUN uv sync --frozen --no-dev --no-editable

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security labels (OCI standard)
LABEL org.opencontainers.image.title="EphemeralShield"
LABEL org.opencontainers.image.description="PostgreSQL JIT credential broker"
LABEL org.opencontainers.image.source="https://github.com/ephemeralshield/ephemeralshield"

# Install only runtime system dependencies
# libpq is required by psycopg3 for PostgreSQL protocol support
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
# WHY non-root? If the app is compromised, the attacker can't modify system
# files, install packages, or access other containers' data as easily.
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/false appuser

WORKDIR /app

# Copy the virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/migrations /app/migrations
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Put the virtual environment's Python on PATH
ENV PATH="/app/.venv/bin:$PATH"
# Tell Python not to buffer stdout/stderr - important for Docker logging
ENV PYTHONUNBUFFERED=1
# Prevent Python from writing .pyc files (not needed in a container)
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose the API port
EXPOSE 8000

# ---------------------------------------------------------------------------
# Default command: Run the API server
# ---------------------------------------------------------------------------
CMD ["uvicorn", "ephemeralshield.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
