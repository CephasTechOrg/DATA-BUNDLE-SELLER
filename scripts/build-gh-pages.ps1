# Build docs/ for GitHub Pages: customer site at /, admin at /admin/
# Run from repo root: .\scripts\build-gh-pages.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $root "frontend\index.html"))) {
    $root = Get-Location
}

# GitHub Pages only serves from a folder named "docs". Your written docs (DEPLOYMENT.md etc.) are in documentation/. This builds the live site into docs/.
$docs = Join-Path $root "docs"
if (Test-Path $docs) { Remove-Item $docs -Recurse -Force }
New-Item -ItemType Directory -Path $docs | Out-Null

# Copy frontend (customer) to docs root
Copy-Item (Join-Path $root "frontend\index.html") $docs
if (Test-Path (Join-Path $root "frontend\style")) { Copy-Item (Join-Path $root "frontend\style") (Join-Path $docs "style") -Recurse -Force }
if (Test-Path (Join-Path $root "frontend\js")) { Copy-Item (Join-Path $root "frontend\js") (Join-Path $docs "js") -Recurse -Force }
if (Test-Path (Join-Path $root "frontend\images")) { Copy-Item (Join-Path $root "frontend\images") (Join-Path $docs "images") -Recurse -Force }

# Copy admin to docs/admin
$docsAdmin = Join-Path $docs "admin"
New-Item -ItemType Directory -Path $docsAdmin -Force | Out-Null
Copy-Item (Join-Path $root "admin\index.html") $docsAdmin
Copy-Item (Join-Path $root "admin\style.css") $docsAdmin
Copy-Item (Join-Path $root "admin\app.js") $docsAdmin

Write-Host "Built site in: docs/"
Write-Host "  - Customer: docs/index.html, docs/style/, docs/js/, docs/images/"
Write-Host "  - Admin:    docs/admin/"
Write-Host ""
Write-Host "Next: Commit and push. In GitHub: Settings > Pages > Source: branch main, folder /docs"
