#!/bin/bash
# Build Script for IDS Consumer API Docker Image

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-ids-connector-sdt}"
IMAGE_TAG="${IMAGE_TAG:-v2.0.4}"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --name) IMAGE_NAME="$2"; shift ;;
        --tag) IMAGE_TAG="$2"; shift ;;
        --help) 
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --name <image-name>  Set Docker image name (default: ids-connector-sdt)"
            echo "  --tag <image-tag>    Set Docker image tag (default: v1.0.0)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   IDS Consumer API - Docker Build Script   ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Image Name: ${IMAGE_NAME}"
echo "  Image Tag:  ${IMAGE_TAG}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found in current directory${NC}"
    exit 1
fi

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Docker image built successfully!${NC}"
    echo -e "${GREEN}  Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    
    # Show image details
    echo ""
    echo -e "${YELLOW}Image Details:${NC}"
    docker images ${IMAGE_NAME}:${IMAGE_TAG}
    
    # Optional: Tag as latest
    #docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
    #echo -e "${GREEN}✓ Also tagged as ${IMAGE_NAME}:latest${NC}"
    
    echo ""
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Run deploy.sh to deploy to Kubernetes"
    echo "  2. Or push to registry: docker push ${IMAGE_NAME}:${IMAGE_TAG}"
else
    echo -e "${RED}✗ Docker image build failed!${NC}"
    echo -e "${RED}Please check the error messages above.${NC}"
    exit 1
fi