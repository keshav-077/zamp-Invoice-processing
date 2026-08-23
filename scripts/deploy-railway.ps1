# Railway deployment helper (run after `railway login`)
#
# Prerequisites:
#   npm install -g @railway/cli
#   railway login
#   Push latest code to GitHub
#
# Usage (from repo root):
#   .\scripts\deploy-railway.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Creating Railway project (if not linked)..."
if (-not (Test-Path ".railway")) {
    railway init --name invoice-processing
}

Write-Host ""
Write-Host "=== Manual steps in Railway dashboard ==="
Write-Host "1. Add PostgreSQL plugin to the project"
Write-Host "2. Create API service:"
Write-Host "   - Root directory: repository root"
Write-Host "   - Config: apps/api/railway.toml"
Write-Host "   - Volume: mount /data/uploads"
Write-Host "   - Env: DATABASE_URL (postgresql+asyncpg://...), STORAGE_PATH=/data/uploads"
Write-Host "   - Env: USE_MOCK_EXTRACTION=false, JWT_SECRET, CORS_ORIGINS, API keys"
Write-Host "3. Create Web service:"
Write-Host "   - Root directory: apps/web"
Write-Host "   - Config: apps/web/railway.toml"
Write-Host "   - Build arg: NEXT_PUBLIC_API_URL=<api public URL>"
Write-Host "4. Set API CORS_ORIGINS to web public URL"
Write-Host ""
Write-Host "Deploy API:"
Write-Host "  railway up --service api"
Write-Host "Deploy Web:"
Write-Host "  railway up --service web --path apps/web"
