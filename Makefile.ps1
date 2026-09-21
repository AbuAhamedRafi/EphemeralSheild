<#
.SYNOPSIS
    EphemeralShield - Windows PowerShell Development Helper (Makefile.ps1)

.DESCRIPTION
    Provides Windows-native equivalents of all Makefile targets.
    Run: .\Makefile.ps1 <target>

.EXAMPLE
    .\Makefile.ps1 help
    .\Makefile.ps1 setup
    .\Makefile.ps1 dev-up
    .\Makefile.ps1 check
#>

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [ValidateSet("help", "setup", "dev-up", "dev-down", "dev-restart", "migrate", "lint", "fmt", "typecheck", "test-unit", "test-all", "check", "clean", "clean-volumes")]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

$COMPOSE_FILE = "deploy/compose.dev.yaml"
$PYTHON = "C:\Users\Rafi\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe"
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

function Invoke-PythonModule([string]$Module, [string[]]$Arguments) {
    $env:PYTHONPATH = "$PSScriptRoot\.venv\Lib\site-packages;$PSScriptRoot\src"
    & $PYTHON -m $Module @Arguments
}

switch ($Target) {
    "help" {
        Write-Host "EphemeralShield Development Commands (PowerShell)" -ForegroundColor Cyan
        Write-Host "=================================================" -ForegroundColor Cyan
        Write-Host "  .\Makefile.ps1 setup        - Install dependencies and generate local secrets"
        Write-Host "  .\Makefile.ps1 dev-up       - Start Docker services (broker-db, test-target-db, redis, api)"
        Write-Host "  .\Makefile.ps1 dev-down     - Stop Docker services"
        Write-Host "  .\Makefile.ps1 dev-restart  - Restart Docker services"
        Write-Host "  .\Makefile.ps1 migrate      - Run Alembic migrations on broker-db"
        Write-Host "  .\Makefile.ps1 lint         - Run Ruff linter"
        Write-Host "  .\Makefile.ps1 fmt          - Auto-format code with Ruff"
        Write-Host "  .\Makefile.ps1 typecheck    - Run mypy strict type checking"
        Write-Host "  .\Makefile.ps1 test-unit    - Run unit tests"
        Write-Host "  .\Makefile.ps1 test-all     - Run all tests"
        Write-Host "  .\Makefile.ps1 check        - Run lint + typecheck + unit tests"
        Write-Host "  .\Makefile.ps1 clean        - Remove Python build artifacts and caches"
        Write-Host "  .\Makefile.ps1 clean-volumes- Remove Docker volumes (destroys data)"
    }

    "setup" {
        Write-Host "Setting up EphemeralShield..." -ForegroundColor Green
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            uv sync
        } else {
            Write-Host "uv not found in PATH; using existing .venv" -ForegroundColor Yellow
        }
        if (-not (Test-Path ".env")) {
            Copy-Item ".env.example" ".env"
            Write-Host "Created .env from .env.example" -ForegroundColor Green
        }
        if (-not (Test-Path "secrets")) {
            & "scripts/generate-secrets.ps1"
        }
        Write-Host "Setup complete. Run .\Makefile.ps1 dev-up to start Docker services." -ForegroundColor Green
    }

    "dev-up" {
        Write-Host "Starting Docker services..." -ForegroundColor Green
        docker compose -f $COMPOSE_FILE up -d --build --wait
        Write-Host "All services are up and healthy." -ForegroundColor Green
        Write-Host "  broker-db:      localhost:5433"
        Write-Host "  test-target-db: localhost:5434"
        Write-Host "  redis:          localhost:6379"
        Write-Host "  API:            localhost:8000"
    }

    "dev-down" {
        Write-Host "Stopping Docker services..." -ForegroundColor Yellow
        docker compose -f $COMPOSE_FILE down
        Write-Host "All services stopped. Data volumes preserved." -ForegroundColor Green
    }

    "dev-restart" {
        & $PSCommandPath dev-down
        & $PSCommandPath dev-up
    }

    "migrate" {
        Write-Host "Running Alembic migrations..." -ForegroundColor Green
        docker compose -f $COMPOSE_FILE exec api alembic upgrade head
        Write-Host "Migrations complete." -ForegroundColor Green
    }

    "lint" {
        Write-Host "Running Ruff linter..." -ForegroundColor Green
        Invoke-PythonModule "ruff" @("check", "src/", "tests/")
        Write-Host "Lint passed." -ForegroundColor Green
    }

    "fmt" {
        Write-Host "Formatting code with Ruff..." -ForegroundColor Green
        Invoke-PythonModule "ruff" @("format", "src/", "tests/")
        Invoke-PythonModule "ruff" @("check", "--fix", "src/", "tests/")
        Write-Host "Format complete." -ForegroundColor Green
    }

    "typecheck" {
        Write-Host "Running mypy type check..." -ForegroundColor Green
        Invoke-PythonModule "mypy" @("src/")
        Write-Host "Type check passed." -ForegroundColor Green
    }

    "test-unit" {
        Write-Host "Running unit tests..." -ForegroundColor Green
        Invoke-PythonModule "pytest" @("tests/unit/", "-v")
    }

    "test-all" {
        Write-Host "Running all tests..." -ForegroundColor Green
        Invoke-PythonModule "pytest" @("tests/", "-v")
    }

    "check" {
        Write-Host "Running full check (lint + typecheck + unit tests)..." -ForegroundColor Cyan
        & $PSCommandPath lint
        & $PSCommandPath typecheck
        & $PSCommandPath test-unit
        Write-Host "All checks passed!" -ForegroundColor Green
    }

    "clean" {
        Write-Host "Cleaning caches..." -ForegroundColor Yellow
        Get-ChildItem -Path . -Include __pycache__,.mypy_cache,.ruff_cache,.pytest_cache -Recurse -Directory -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
        Remove-Item -Path "dist", "build", "htmlcov", ".coverage" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Cleaned." -ForegroundColor Green
    }

    "clean-volumes" {
        Write-Host "Destroying Docker volumes..." -ForegroundColor Red
        docker compose -f $COMPOSE_FILE down -v
        Write-Host "Volumes destroyed." -ForegroundColor Green
    }
}
