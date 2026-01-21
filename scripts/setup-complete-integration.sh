#!/bin/bash

# Smart Presence AI - Complete Integration Setup Script
# This script sets up the entire enhanced system with AI chatbot and N8N automation

set -e

echo "🚀 Smart Presence AI - Complete Integration Setup"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_status "Docker is running"

# Check if .env files exist
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from example..."
    cp .env.example .env
    print_info "Please edit .env file with your API keys before running the system"
fi

if [ ! -f backend/.env ]; then
    print_warning "backend/.env file not found. Creating from example..."
    cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
    print_warning "frontend/.env file not found. Creating from example..."
    cp frontend/.env.example frontend/.env
fi

# Build and start services
print_info "Building and starting Docker services..."
docker-compose up -d --build

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 30

# Check service health
print_info "Checking service health..."

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend is healthy"
else
    print_error "Backend is not responding"
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_status "Frontend is healthy"
else
    print_warning "Frontend might still be starting..."
fi

# Run database migrations
print_info "Running database migrations..."
docker-compose exec backend alembic upgrade head

# Seed ChromaDB with knowledge base
print_info "Seeding AI knowledge base..."
docker-compose exec backend python -m app.scripts.seed_chromadb

# Check chatbot status
print_info "Checking chatbot status..."
CHATBOT_STATUS=$(curl -s http://localhost:8000/api/chatbot/status | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$CHATBOT_STATUS" = "ok" ]; then
    print_status "AI Chatbot is ready"
else
    print_warning "Chatbot status: $CHATBOT_STATUS"
fi

# Check N8N integration
print_info "Checking N8N integration endpoints..."
if curl -f http://localhost:8000/api/n8n/pdfs/recent > /dev/null 2>&1; then
    print_status "N8N integration endpoints are ready"
else
    print_warning "N8N endpoints might need configuration"
fi

# Display access information
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
print_info "Access URLs:"
echo "  • Frontend: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • AI Chatbot: http://localhost:3000/chat"
echo ""
print_info "AI Chatbot Endpoints:"
echo "  • Status: GET http://localhost:8000/api/chatbot/status"
echo "  • Chat: POST http://localhost:8000/api/chatbot/ask"
echo "  • Streaming: POST http://localhost:8000/api/chatbot/stream"
echo ""
print_info "N8N Integration:"
echo "  • PDF Upload: POST http://localhost:8000/api/upload"
echo "  • Recent PDFs: GET http://localhost:8000/api/pdfs/recent"
echo "  • Enhanced workflows: scripts/enhanced-n8n-workflows.json"
echo ""
print_warning "Important Notes:"
echo "  • Configure your API keys in .env files (GROQ_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY)"
echo "  • Import enhanced N8N workflows from scripts/enhanced-n8n-workflows.json"
echo "  • Configure N8N webhook URLs to point to http://localhost:8000/api/n8n"
echo "  • Gotenberg PDF service is available at http://localhost:3001"
echo ""
print_status "System is ready for use!"

# Display next steps
echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Configure API keys in .env files"
echo "2. Test the AI chatbot at http://localhost:3000/chat"
echo "3. Import N8N workflows for automation"
echo "4. Configure N8N webhooks and credentials"
echo "5. Test facial recognition and check-in features"
echo ""

# Optional: Run tests
read -p "Do you want to run integration tests? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running integration tests..."
    ./scripts/test-n8n-integration.sh
fi

echo ""
print_status "Smart Presence AI integration setup completed successfully! 🎯"
