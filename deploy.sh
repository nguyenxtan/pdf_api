#!/bin/bash

# Quick deploy script for VPS Ubuntu
# Usage: curl -fsSL https://raw.githubusercontent.com/nguyenxtan/pdf_api/main/deploy.sh | bash

set -e

echo "==================================="
echo "PDF API - Quick Deploy Script"
echo "==================================="

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: This script is designed for Linux (Ubuntu/Debian)"
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

# Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose already installed"
fi

# Clone or update repository
REPO_DIR="$HOME/pdf_api"

if [ -d "$REPO_DIR" ]; then
    echo "Repository exists, pulling latest changes..."
    cd "$REPO_DIR"
    git pull
else
    echo "Cloning repository..."
    cd "$HOME"
    git clone https://github.com/nguyenxtan/pdf_api.git
    cd "$REPO_DIR"
fi

# Stop existing container if running
if docker ps -a | grep -q pdf-api; then
    echo "Stopping existing container..."
    docker compose down
fi

# Build and start
echo "Building and starting PDF API..."
docker compose up -d --build

# Wait for service to be ready
echo "Waiting for service to start..."
sleep 5

# Health check
echo ""
echo "==================================="
echo "Checking service health..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ Service is healthy and running!"
    echo ""
    echo "API is accessible at: http://localhost:8000"
    echo "API Documentation: http://localhost:8000/docs"
    echo ""
    echo "To view logs: docker compose logs -f"
    echo "To stop: docker compose down"
    echo ""

    # Show server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "If you want to access from outside:"
    echo "  http://$SERVER_IP:8000"
    echo ""
    echo "For production setup with Nginx + SSL, see DEPLOY.md"
else
    echo "✗ Service health check failed"
    echo "Check logs with: docker compose logs pdf-api"
    exit 1
fi

echo "==================================="
echo "Deployment complete!"
echo "==================================="
