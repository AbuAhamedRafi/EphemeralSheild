#!/usr/bin/env bash
# =============================================================================
# EphemeralShield — Local Secret Generation (Bash)
# =============================================================================
# This script generates local development secrets that are NEVER committed
# to Git. It creates:
#   1. .env file from .env.example with random passwords
#   2. secrets/ directory with Ed25519 signing key pair
#
# Usage: bash scripts/generate-secrets.sh
#
# SECURITY: This is for LOCAL DEVELOPMENT ONLY.
# Production secrets must come from a proper secret manager.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "EphemeralShield — Generating local development secrets..."

# ---------------------------------------------------------------------------
# Create secrets directory with restrictive permissions
# ---------------------------------------------------------------------------
SECRETS_DIR="$PROJECT_DIR/secrets"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"
echo "  Created secrets/ directory (mode 700)"

# ---------------------------------------------------------------------------
# Generate random passwords
# ---------------------------------------------------------------------------
BROKER_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
TARGET_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# ---------------------------------------------------------------------------
# Create .env from .env.example
# ---------------------------------------------------------------------------
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    sed \
        -e "s/CHANGE_ME_BROKER_PASSWORD/$BROKER_PASSWORD/g" \
        -e "s/CHANGE_ME_TARGET_PASSWORD/$TARGET_PASSWORD/g" \
        "$PROJECT_DIR/.env.example" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "  Created .env with generated passwords (mode 600)"
else
    echo "  .env already exists — skipping (delete it to regenerate)"
fi

# ---------------------------------------------------------------------------
# Generate Ed25519 signing key pair
# ---------------------------------------------------------------------------
KEY_FILE="$SECRETS_DIR/audit-signing.key"
PUB_FILE="$SECRETS_DIR/audit-signing.pub"

if [ ! -f "$KEY_FILE" ]; then
    python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

private_key = Ed25519PrivateKey.generate()

with open('$KEY_FILE', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

with open('$PUB_FILE', 'wb') as f:
    f.write(private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))
"
    chmod 600 "$KEY_FILE"
    chmod 644 "$PUB_FILE"
    echo "  Generated Ed25519 signing key pair"
else
    echo "  Signing keys already exist — skipping"
fi

echo ""
echo "Secret generation complete!"
echo "  .env:                  $ENV_FILE"
echo "  Signing key (private): $KEY_FILE"
echo "  Signing key (public):  $PUB_FILE"
echo ""
echo "REMINDER: These files are gitignored. Never commit them."
