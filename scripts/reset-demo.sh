#!/usr/bin/env bash
# Nightly reset for the hosted public demo (docker-compose.demo.yml).
#
# Wipes the database volume (one visitor's edits don't persist for the next),
# pulls fresh images so the demo tracks main, and brings the stack back up —
# migrate reseeds the demo persona into the empty DB on the way up.
# TLS certs survive: Caddy stores them on bind mounts, which `down -v` ignores.
#
# Cron (4am ET on a UTC box), with a log for the morning-after check:
#   0 9 * * * /srv/firemaster/scripts/reset-demo.sh >> /var/log/firemaster-demo-reset.log 2>&1
#
# ~10-20s of downtime per run.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== demo reset: $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

docker compose -f docker-compose.demo.yml down -v --remove-orphans

# Track main: refresh the backend image (GHCR builds on every push to main).
# --ignore-buildable skips the locally-built frontend image; non-fatal if
# GHCR/network hiccups — the reset still completes on the cached image.
# NB: the frontend does NOT auto-update. To ship frontend changes to the demo:
#   git pull && docker compose -f docker-compose.demo.yml up -d --build frontend
docker compose -f docker-compose.demo.yml pull --quiet --ignore-buildable || true

docker compose -f docker-compose.demo.yml up -d

echo "=== demo reset complete ==="
