#!/bin/bash
# SmartPresence Service Starter - Enhanced Version
# Starts all services with error handling, health checks, and user feedback
# Usage: ./scripts/start.sh

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Trap Ctrl+C for graceful shutdown
trap 'log_warning "Service startup interrupted"; exit 1' INT TERM

log_info "SmartPresence Services - Intelligent Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pre-flight checks
log_info "Running pre-flight checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
  log_error "Docker not installed"
  echo "  Please install Docker from https://docker.com"
  exit 1
fi

# Detect docker compose (v2) or docker-compose (v1)
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
  COMPOSE_CMD=(docker compose)
  COMPOSE_VER=$(docker compose version | grep -oE '[0-9.]+' | head -1)
elif command -v docker-compose &> /dev/null; then
  COMPOSE_CMD=(docker-compose)
  COMPOSE_VER=$(docker-compose --version | grep -oE '[0-9.]+' | head -1)
else
  log_error "Docker Compose not installed"
  echo "  Install Docker Compose (v2 recommended)"
  exit 1
fi

log_success "Docker $(docker --version | awk '{print $NF}')"
log_success "Compose ${COMPOSE_VER}"

# Check .env file
if [ ! -f .env ]; then
  log_warning ".env file not found"
  if [ -f .env.example ]; then
    cp .env.example .env
    log_success "Created .env from template"
    log_warning "Please review and update .env with your settings (SECRET_KEY, etc.)"
  else
    log_error ".env.example not found in $ROOT_DIR"
    exit 1
  fi
fi

# Check for port conflicts
check_port_available() {
  local port=$1
  local service=$2
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port $port already in use (needed by $service)"
    return 1
  fi
  return 0
}

PORTS_CONFLICT=0
check_port_available 3000 "Frontend" || PORTS_CONFLICT=1
check_port_available 8000 "Backend" || PORTS_CONFLICT=1
check_port_available 5432 "Database" || PORTS_CONFLICT=1
check_port_available 6380 "Redis" || PORTS_CONFLICT=1

if [ $PORTS_CONFLICT -eq 1 ]; then
  log_warning "Some ports are already in use"
  log_info "Try: ./scripts/stop.sh (or ./scripts/reset-docker.sh if you need a clean reset)"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Startup cancelled"
    exit 1
  fi
fi

# Start services
echo ""
log_info "Starting services with Docker Compose..."
if ! "${COMPOSE_CMD[@]}" up -d 2>&1; then
  log_error "Failed to start Docker services"
  log_info "Try: docker system prune -af"
  exit 1
fi

log_success "Docker services started"

# Health check with timeout
log_info "Waiting for services to be healthy (max 30 seconds)..."
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=2
ELAPSED=0

while [ $ELAPSED -lt $HEALTH_CHECK_TIMEOUT ]; do
  # Check backend
  if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    log_success "Backend API is responding"
    break
  fi
  
  ELAPSED=$((ELAPSED + HEALTH_CHECK_INTERVAL))
  if [ $ELAPSED -lt $HEALTH_CHECK_TIMEOUT ]; then
    echo -ne "${BLUE}${ELAPSED}/${HEALTH_CHECK_TIMEOUT}s...${NC}\r"
    sleep $HEALTH_CHECK_INTERVAL
  fi
done

if [ $ELAPSED -ge $HEALTH_CHECK_TIMEOUT ]; then
  log_warning "Services took longer than expected to start"
  log_info "Run './scripts/status.sh' to debug"
fi

# Success summary
echo ""
log_success "SmartPresence is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}📍 Access URLs:${NC}"
echo "   Frontend:   ${BLUE}http://localhost:3000${NC}"
echo "   Backend:    ${BLUE}http://localhost:8000${NC}"
echo "   API Docs:   ${BLUE}http://localhost:8000/docs${NC}"
echo "   Database:   ${BLUE}postgres://localhost:5432${NC}"
echo "   Redis:      ${BLUE}localhost:6380${NC}"
echo "   Gotenberg:  ${BLUE}http://localhost:3001/health${NC} (PDF service for N8N)"
echo ""
echo -e "${BLUE}📚 Useful commands:${NC}"
echo "   ./scripts/status.sh   - Check service health"
echo "   ./scripts/logs.sh     - View service logs"
echo "   ./scripts/shell.sh    - Open service shells"
echo "   ./scripts/stop.sh     - Stop all services"
echo "   ./scripts/rebuild.sh  - Rebuild images (when needed)"
echo "   ./scripts/reset-docker.sh - Free space / clean reset"
echo ""
