# =============================================================================
# EphemeralShield — Local Secret Generation (PowerShell)
# =============================================================================
# This script generates local development secrets that are NEVER committed
# to Git. It creates:
#   1. .env file from .env.example with random passwords
#   2. secrets/ directory with Ed25519 signing key pair
#
# Usage: powershell -File scripts/generate-secrets.ps1
#
# SECURITY: This is for LOCAL DEVELOPMENT ONLY.
# Production secrets must come from a proper secret manager.
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "EphemeralShield — Generating local development secrets..." -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Create secrets directory
# ---------------------------------------------------------------------------
$secretsDir = Join-Path $PSScriptRoot ".." "secrets"
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null
    Write-Host "  Created secrets/ directory" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Generate random passwords using Python's secrets module
# ---------------------------------------------------------------------------
# WHY Python's secrets module? It uses cryptographically secure randomness
# (os.urandom), unlike PowerShell's Get-Random which uses a PRNG.
# ---------------------------------------------------------------------------
$brokerPassword = python -c "import secrets; print(secrets.token_urlsafe(32))"
$targetPassword = python -c "import secrets; print(secrets.token_urlsafe(32))"

# ---------------------------------------------------------------------------
# Create .env from .env.example with real secrets
# ---------------------------------------------------------------------------
$envExample = Join-Path $PSScriptRoot ".." ".env.example"
$envFile = Join-Path $PSScriptRoot ".." ".env"

if (-not (Test-Path $envFile)) {
    $content = Get-Content $envExample -Raw
    $content = $content -replace "CHANGE_ME_BROKER_PASSWORD", $brokerPassword
    $content = $content -replace "CHANGE_ME_TARGET_PASSWORD", $targetPassword
    Set-Content -Path $envFile -Value $content -NoNewline
    Write-Host "  Created .env with generated passwords" -ForegroundColor Green
} else {
    Write-Host "  .env already exists — skipping (delete it to regenerate)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Generate Ed25519 signing key pair for audit checkpoints
# ---------------------------------------------------------------------------
# WHY Ed25519? It's the recommended modern signature algorithm:
#   - 256-bit security (equivalent to RSA-3072)
#   - Fast signing and verification
#   - Small key sizes (32 bytes)
#   - Not vulnerable to timing attacks
# ---------------------------------------------------------------------------
$keyFile = Join-Path $secretsDir "audit-signing.key"
$pubFile = Join-Path $secretsDir "audit-signing.pub"

if (-not (Test-Path $keyFile)) {
    python -c @"
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

private_key = Ed25519PrivateKey.generate()

# Write private key (PEM format, no encryption for dev)
with open(r'$keyFile', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Write public key
with open(r'$pubFile', 'wb') as f:
    f.write(private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))
"@
    Write-Host "  Generated Ed25519 signing key pair" -ForegroundColor Green
} else {
    Write-Host "  Signing keys already exist — skipping" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Secret generation complete!" -ForegroundColor Cyan
Write-Host "  .env:                    $(Resolve-Path (Join-Path $PSScriptRoot '..' '.env'))"
Write-Host "  Signing key (private):   $(Resolve-Path $keyFile)"
Write-Host "  Signing key (public):    $(Resolve-Path $pubFile)"
Write-Host ""
Write-Host "REMINDER: These files are gitignored. Never commit them." -ForegroundColor Yellow
