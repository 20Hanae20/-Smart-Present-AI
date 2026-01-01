#!/bin/bash
# SmartPresence Service Stopper - Enhanced Version
# Stops all services with graceful shutdown and cleanup options
# Usage: ./scripts/stop.sh

# Color codes
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Trap Ctrl+C
trap 'log_warning "Shutdown interrupted"; exit 1' INT TERM

log_info "SmartPresence Services - Graceful Shutdown"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Detect compose command
if docker compose version >/dev/null 2>&1; then COMPOSE_CMD=(docker compose); else COMPOSE_CMD=(docker-compose); fi

# Check if services are running
if ! "${COMPOSE_CMD[@]}" ps 2>/dev/null | grep -q "smartpresence"; then
  log_warning "No services currently running"
  exit 0
fi

# Count running containers
RUNNING=$("${COMPOSE_CMD[@]}" ps --quiet 2>/dev/null | wc -l)
if [ "$RUNNING" -gt 0 ]; then
  log_info "Found $RUNNING running container(s)"
  log_info "Stopping services (this may take up to 10 seconds)..."
  echo ""
  
  # Stop containers with timeout
  if "${COMPOSE_CMD[@]}" down --timeout 10 2>&1; then
    log_success "All services stopped gracefully"
  else
    log_warning "Some services required forced shutdown"
    "${COMPOSE_CMD[@]}" kill 2>/dev/null || true
    "${COMPOSE_CMD[@]}" down 2>/dev/null || true
    log_success "Services stopped"
  fi
else
  log_warning "No running services found"
fi

echo ""

echo "Cleanup options:"
echo "  [n] None (default)"
echo "  [c] Chroma only (vector store reset)"
echo "  [a] All volumes (DB, Redis, uploads, Chroma)"
read -p "Choose cleanup option [n/c/a]: " -n 1 -r CHOICE
echo ""

case "$CHOICE" in
  c|C)
    log_info "Removing Chroma vector volumes..."
    # Best-effort removal of Chroma volumes for both main and ntic2
    VOLS=$(docker volume ls --format '{{.Name}}' | grep -E '_chroma_data$' || true)
    if [ -n "$VOLS" ]; then
      echo "$VOLS" | xargs -r docker volume rm >/dev/null 2>&1 || true
      log_success "Chroma volumes removed"
      log_warning "Knowledge base will be reseeded on next start"
    else
      log_info "No Chroma volumes found"
    fi
    ;;
  a|A)
    log_info "Removing ALL compose volumes..."
    VOLUMES=$("${COMPOSE_CMD[@]}" config --volumes 2>/dev/null | tail -n +2 | wc -l)
    if "${COMPOSE_CMD[@]}" down -v 2>/dev/null; then
      log_success "Volumes removed ($VOLUMES volumes cleaned)"
      log_warning "Database and uploads have been deleted"
    else
      log_error "Failed to remove volumes"
      exit 1
    fi
    ;;
  *)
    log_info "Keeping volumes and data for next startup"
    ;;
esac

echo ""
log_success "SmartPresence shutdown complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}To start services again:${NC}"
echo "   ./scripts/start.sh"
echo ""
