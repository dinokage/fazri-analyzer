#!/usr/bin/env bash
###############################################################################
# FAZRI production deploy script
#
# Usage: bash scripts/deploy.sh [--no-pull]
#   --no-pull  Skip docker compose pull (use locally built images)
###############################################################################
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"
ENV_FILE="$REPO_ROOT/.env.prod"
ENV_EXAMPLE="$REPO_ROOT/.env.prod.example"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Step 0: Preflight ─────────────────────────────────────────────────────────

command -v docker >/dev/null 2>&1 || error "docker not found. Install Docker first."
docker compose version >/dev/null 2>&1 || error "docker compose plugin not found."

# ── Step 1: Ensure .env.prod exists ──────────────────────────────────────────

if [[ ! -f "$ENV_FILE" ]]; then
  warn ".env.prod not found — copying from .env.prod.example"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  warn "Please edit .env.prod and fill in all [REQUIRED] values, then re-run."
  exit 1
fi

# Warn if any [REQUIRED] placeholder is still present
if grep -q "CHANGE_ME" "$ENV_FILE" 2>/dev/null; then
  warn ".env.prod still contains CHANGE_ME placeholders. Double-check before production use."
fi

info "Using env file: $ENV_FILE"

# ── Step 2: Pull latest images (unless skipped) ───────────────────────────────

if [[ "${1:-}" != "--no-pull" ]]; then
  info "Pulling latest images..."
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull --ignore-pull-failures
fi

# ── Step 3: Build images ──────────────────────────────────────────────────────

info "Building backend, frontend, deepface-server..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build \
  backend frontend deepface-server

# ── Step 4: Start / update services ──────────────────────────────────────────

info "Starting stack..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --remove-orphans

# ── Step 5: Wait for health checks ───────────────────────────────────────────

info "Waiting for services to become healthy (up to 120s)..."
DEADLINE=$(( $(date +%s) + 120 ))
SERVICES=(postgres pgvector redis neo4j backend)

for SVC in "${SERVICES[@]}"; do
  while true; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' "fazri_${SVC}" 2>/dev/null || echo "missing")
    if [[ "$STATUS" == "healthy" ]]; then
      info "$SVC: healthy"
      break
    fi
    if (( $(date +%s) > DEADLINE )); then
      warn "$SVC health check timed out (status=$STATUS) — check logs with: docker logs fazri_${SVC}"
      break
    fi
    sleep 3
  done
done

# ── Step 6: Run database migrations ──────────────────────────────────────────

info "Running backend database migrations..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  python -c "
from database.connection import init_db
init_db()
print('init_db OK')
" && info "DB init complete" || warn "DB init failed — check backend logs"

# Sensor events table
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  python migrations/create_sensor_events.py \
  && info "sensor_events migration OK" || warn "sensor_events migration skipped/failed"

# Entity tables
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  python migrations/create_entity_tables.py \
  && info "entity_tables migration OK" || warn "entity_tables migration skipped/failed"

# ── Step 7: Print status ──────────────────────────────────────────────────────

echo ""
info "=== FAZRI Stack Status ==="
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
echo ""
info "Frontend:  https://your-domain.edu (port 443)"
info "API docs:  https://your-domain.edu/api/docs"
info "Neo4j UI:  Not exposed (internal only)"
info ""
info "To view logs:  docker compose -f docker-compose.prod.yml logs -f <service>"
info "To stop:       docker compose -f docker-compose.prod.yml down"
