#!/bin/bash
# =============================================================================
# SecDash Setup Script
# =============================================================================

set -e

echo "🚀 Setting up SecDash..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created. Please edit it with your configuration.${NC}"
    echo -e "${YELLOW}⚠️  Don't forget to set secure passwords and API tokens!${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Pulling Ollama models...${NC}"
echo "This may take a while depending on your internet connection."

# Start Ollama service
docker-compose up -d ollama
sleep 5

# Pull Ollama models
echo -e "${BLUE}Pulling llama3.2...${NC}"
docker exec secdash_ollama ollama pull llama3.2 || echo "Warning: Failed to pull llama3.2"

echo -e "${BLUE}Pulling codellama...${NC}"
docker exec secdash_ollama ollama pull codellama || echo "Warning: Failed to pull codellama"

echo -e "${BLUE}Pulling deepseek-coder...${NC}"
docker exec secdash_ollama ollama pull deepseek-coder || echo "Warning: Failed to pull deepseek-coder"

echo -e "${GREEN}✅ Ollama models setup completed!${NC}"

# Start all services
echo -e "${BLUE}🐳 Starting all services...${NC}"
docker-compose up -d

echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Run database migrations
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
docker-compose exec -T backend alembic upgrade head || echo "Warning: Migrations will run on first backend start"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 SecDash setup completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Access the application:${NC}"
echo -e "  Frontend: http://localhost:3000"
echo -e "  Backend API: http://localhost:8000"
echo -e "  API Docs: http://localhost:8000/docs"
echo -e "  Ollama: http://localhost:11434"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs: docker-compose logs -f"
echo -e "  Stop services: docker-compose down"
echo -e "  Restart services: docker-compose restart"
echo -e "  View status: docker-compose ps"
echo ""
