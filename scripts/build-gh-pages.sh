#!/usr/bin/env bash
# Build docs/ for GitHub Pages (GitHub only serves from a folder named "docs").
# Your written docs (DEPLOYMENT.md etc.) live in documentation/. This script puts the
# customer + admin site into docs/ so Pages can serve them.
# Run from repo root: bash scripts/build-gh-pages.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$ROOT/docs"

rm -rf "$DOCS"
mkdir -p "$DOCS"

# Customer frontend -> docs root (site home)
cp "$ROOT/frontend/index.html" "$DOCS/"
[ -d "$ROOT/frontend/style" ]  && cp -r "$ROOT/frontend/style" "$DOCS/"
[ -d "$ROOT/frontend/js" ]     && cp -r "$ROOT/frontend/js" "$DOCS/"
[ -d "$ROOT/frontend/images" ] && cp -r "$ROOT/frontend/images" "$DOCS/"

# Admin -> docs/admin
mkdir -p "$DOCS/admin"
cp "$ROOT/admin/index.html" "$ROOT/admin/style.css" "$ROOT/admin/app.js" "$DOCS/admin/"

echo "Built site in: docs/"
echo "  - Customer: docs/index.html, docs/style/, docs/js/, docs/images/"
echo "  - Admin:    docs/admin/"
echo ""
echo "Next: Commit and push. In GitHub: Settings > Pages > Source: branch main, folder /docs"
