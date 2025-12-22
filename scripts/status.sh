#!/bin/bash
# SmartPresence Service Status Checker - Enhanced Version
# Displays comprehensive health status with diagnostics and suggestions
# Usage: ./scripts/status.sh [service]

# Color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log_info "SmartPresence System Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Container status
echo -e "${YELLOW}🐳 Container Status:${NC}"
# Detect compose command (v2 preferred)
if docker compose version >/dev/null 2>&1; then COMPOSE_CMD=(docker compose); else COMPOSE_CMD=(docker-compose); fi

if ! "${COMPOSE_CMD[@]}" ps 2>/dev/null | grep -q -E "postgres|redis|backend|frontend"; then
  log_warn "No containers running"
  echo "   Run: ./scripts/start.sh"
  echo ""
  exit 0
fi

# docker-compose v1 doesn't support --format, so keep this portable.
"${COMPOSE_CMD[@]}" ps 2>/dev/null || log_error "Failed to get container status"

echo ""

# Port availability with enhanced checks
echo -e "${YELLOW}🔌 Port Availability:${NC}"

get_host_port() {
  local service=$1
  local internal_port=$2
  local container
  container=$(${COMPOSE_CMD[@]} ps -q "$service" 2>/dev/null | head -n 1)
  if [ -z "$container" ]; then
    return 1
  fi

  local mapping
  mapping=$(docker port "$container" "${internal_port}/tcp" 2>/dev/null | head -n 1)
  if [ -z "$mapping" ]; then
    return 1
  fi

  # mapping examples: 0.0.0.0:3000 or :::3000
  echo "$mapping" | awk -F: '{print $NF}'
  return 0
}

check_port_mapping() {
  local service=$1
  local internal_port=$2
  local label=$3
  local container
  container=$(${COMPOSE_CMD[@]} ps -q "$service" 2>/dev/null | head -n 1)
  if [ -z "$container" ]; then
    echo -e "   ${RED}✗${NC} ${label}: container not found"
    return 1
  fi

  local mapping
  mapping=$(docker port "$container" "${internal_port}/tcp" 2>/dev/null | head -n 1)

  if [ -n "$mapping" ]; then
    echo -e "   ${GREEN}✓${NC} ${label}: $mapping"
    return 0
  fi

  echo -e "   ${RED}✗${NC} ${label}: not published"
  return 1
}

check_port_mapping frontend 3000 "Frontend"
check_port_mapping backend 8000 "Backend API"
check_port_mapping postgres 5432 "PostgreSQL"
check_port_mapping redis 6379 "Redis"
check_port_mapping gotenberg 3000 "Gotenberg (PDF)"

echo ""

# Service health check with detailed diagnostics
echo -e "${YELLOW}🏥 Service Health:${NC}"

FRONTEND_OK=0
BACKEND_OK=0
POSTGRES_OK=0
REDIS_OK=0
GOTENBERG_OK=0

# Frontend
echo -n "   Frontend (3000): "
FRONTEND_PORT=$(get_host_port frontend 3000 || true)
if [ -n "$FRONTEND_PORT" ] && (curl -s -m 5 "http://localhost:${FRONTEND_PORT}" > /dev/null 2>&1 || curl -s -m 5 "http://localhost:${FRONTEND_PORT}" > /dev/null 2>&1); then
  log_success "Responding"
  FRONTEND_OK=1
else
  log_error "Not responding"
  log_warn "   → Check: ./scripts/logs.sh frontend"
fi

# Backend API
echo -n "   Backend (8000): "
BACKEND_PORT=$(get_host_port backend 8000 || true)
if [ -n "$BACKEND_PORT" ] && curl -s -m 2 "http://localhost:${BACKEND_PORT}/docs" > /dev/null 2>&1; then
  log_success "API responding"
  BACKEND_OK=1
else
  log_error "API not responding"
  log_warn "   → Check: ./scripts/logs.sh backend"
fi

# PostgreSQL connectivity
echo -n "   PostgreSQL (5432): "
if "${COMPOSE_CMD[@]}" exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
  TABLES=$("${COMPOSE_CMD[@]}" exec -T postgres psql -U postgres -d smartpresence -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "?")
  log_success "Connected ($TABLES tables)"
  POSTGRES_OK=1
else
  log_error "Not responding"
  log_warn "   → Check: docker-compose logs postgres"
fi

# Redis connectivity
echo -n "   Redis (6379): "
if "${COMPOSE_CMD[@]}" exec -T redis redis-cli ping > /dev/null 2>&1; then
  INFO=$("${COMPOSE_CMD[@]}" exec -T redis redis-cli info 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
  log_success "Connected (${INFO:-?} used)"
  REDIS_OK=1
else
  log_error "Not responding"
  log_warn "   → Check: docker-compose logs redis"
fi

# Gotenberg (PDF service for N8N)
echo -n "   Gotenberg (3001): "
if curl -s -m 2 "http://localhost:3001/health" > /dev/null 2>&1; then
  log_success "PDF service ready"
  GOTENBERG_OK=1
else
  log_error "Not responding"
  log_warn "   → Check: docker-compose logs gotenberg"
fi

echo ""

# System diagnostics
echo -e "${YELLOW}📊 System Diagnostics:${NC}"
# Container count
RUNNING=0
for svc in postgres redis backend frontend gotenberg; do
  cid=$(${COMPOSE_CMD[@]} ps -q "$svc" 2>/dev/null | head -n 1)
  if [ -n "$cid" ] && docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null | grep -q true; then
    RUNNING=$((RUNNING + 1))
  fi
done
echo "   Running Containers: $RUNNING/5"

# Overall status
echo ""
if [ "$RUNNING" -ne 5 ]; then
  if [ "$RUNNING" -gt 0 ]; then
    log_warn "Partial startup - $((5 - RUNNING)) service(s) missing"
  else
    log_error "No services running"
    echo "   Run: ./scripts/start.sh"
  fi
elif [ "$FRONTEND_OK" -eq 1 ] && [ "$BACKEND_OK" -eq 1 ] && [ "$POSTGRES_OK" -eq 1 ] && [ "$REDIS_OK" -eq 1 ] && [ "$GOTENBERG_OK" -eq 1 ]; then
  log_success "All services online"
else
  log_warn "Containers up, but one or more health checks failed"
fi

echo ""
echo -e "${BLUE}📚 Quick Links:${NC}"
echo "   Frontend:   http://localhost:3000"
echo "   Backend:    http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Gotenberg:  http://localhost:3001/health (PDF service)"
echo ""
echo -e "${BLUE}📚 Quick Links:${NC}"
echo "   Frontend:   http://localhost:3000"
echo "   Backend:    http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo ""

echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo "   ./scripts/logs.sh backend    - View backend logs"
echo "   ./scripts/logs.sh frontend   - View frontend logs"
echo "   ./scripts/shell.sh backend   - Open backend shell"
echo "   ./scripts/stop.sh            - Stop all services"
echo ""
