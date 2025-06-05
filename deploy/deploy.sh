#!/bin/bash

# Contact Extraction App Deployment Script for EC2
# This script automates the deployment of the containerized application

set -e  # Exit on any error

# Configuration
APP_NAME="contact-extraction-app"
DOCKER_IMAGE="contact-extraction:latest"
CONTAINER_NAME="contact-extraction-container"
HOST_PORT="8501"
CONTAINER_PORT="8501"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if Docker is installed
check_docker() {
    log "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    log "Docker is installed ✓"
}

# Check if Docker Compose is installed
check_docker_compose() {
    log "Checking Docker Compose installation..."
    if ! command -v docker-compose &> /dev/null; then
        warning "Docker Compose is not installed. Installing..."
        sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    log "Docker Compose is available ✓"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y curl wget git unzip
    log "System dependencies installed ✓"
}

# Stop and remove existing container
cleanup_existing() {
    log "Cleaning up existing containers..."
    
    # Stop container if running
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        log "Stopping existing container..."
        docker stop $CONTAINER_NAME
    fi
    
    # Remove container if exists
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        log "Removing existing container..."
        docker rm $CONTAINER_NAME
    fi
    
    log "Cleanup completed ✓"
}

# Build Docker image
build_image() {
    log "Building Docker image..."
    docker build -t $DOCKER_IMAGE .
    log "Docker image built successfully ✓"
}

# Run the container
run_container() {
    log "Starting new container..."
    
    # Create directories for volumes
    mkdir -p uploads outputs
    
    # Run the container
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $HOST_PORT:$CONTAINER_PORT \
        -v $(pwd)/uploads:/app/uploads \
        -v $(pwd)/outputs:/app/outputs \
        $DOCKER_IMAGE
    
    log "Container started successfully ✓"
}

# Check container health
check_health() {
    log "Checking container health..."
    sleep 10  # Wait for container to start
    
    for i in {1..30}; do
        if curl -f http://localhost:$HOST_PORT/_stcore/health &> /dev/null; then
            log "Application is healthy and running ✓"
            return 0
        fi
        sleep 2
    done
    
    error "Application health check failed"
}

# Show container logs
show_logs() {
    log "Container logs:"
    docker logs $CONTAINER_NAME --tail 20
}

# Show deployment info
show_info() {
    log "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
    echo ""
    echo "🚀 Application Details:"
    echo "   - Container Name: $CONTAINER_NAME"
    echo "   - Image: $DOCKER_IMAGE"
    echo "   - Port: $HOST_PORT"
    echo ""
    echo "🌐 Access URLs:"
    echo "   - Local: http://localhost:$HOST_PORT"
    echo "   - Public: http://$(curl -s ifconfig.me):$HOST_PORT"
    echo ""
    echo "📁 Directories:"
    echo "   - Uploads: $(pwd)/uploads"
    echo "   - Outputs: $(pwd)/outputs"
    echo ""
    echo "🔧 Useful Commands:"
    echo "   - View logs: docker logs $CONTAINER_NAME"
    echo "   - Stop app: docker stop $CONTAINER_NAME"
    echo "   - Start app: docker start $CONTAINER_NAME"
    echo "   - Restart app: docker restart $CONTAINER_NAME"
    echo ""
}

# Main deployment function
main() {
    log "Starting Contact Extraction App deployment..."
    
    check_docker
    check_docker_compose
    install_dependencies
    cleanup_existing
    build_image
    run_container
    check_health
    show_info
    
    log "Deployment completed successfully! 🎉"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log "Stopping application..."
        docker stop $CONTAINER_NAME || true
        log "Application stopped ✓"
        ;;
    "start")
        log "Starting application..."
        docker start $CONTAINER_NAME || error "Container not found. Run deploy first."
        log "Application started ✓"
        ;;
    "restart")
        log "Restarting application..."
        docker restart $CONTAINER_NAME || error "Container not found. Run deploy first."
        check_health
        log "Application restarted ✓"
        ;;
    "logs")
        show_logs
        ;;
    "status")
        log "Container status:"
        docker ps -f name=$CONTAINER_NAME
        ;;
    "clean")
        log "Cleaning up all resources..."
        cleanup_existing
        docker rmi $DOCKER_IMAGE || true
        log "Cleanup completed ✓"
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|logs|status|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  start   - Start existing container"
        echo "  stop    - Stop running container"
        echo "  restart - Restart container"
        echo "  logs    - Show container logs"
        echo "  status  - Show container status"
        echo "  clean   - Remove all resources"
        exit 1
        ;;
esac 