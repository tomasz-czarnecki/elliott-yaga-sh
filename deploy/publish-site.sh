#!/usr/bin/env bash
# Refresh site/data and publish it: the push to main makes Vercel redeploy the site.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
git pull --ff-only
.venv/bin/ewave-data export-site
git add site/data
git commit -m "Update site data"
git push
