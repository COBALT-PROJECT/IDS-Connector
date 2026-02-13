#!/bin/bash

# Build Script for IDS TOE Provider API

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="ids-connector-toe"
IMAGE_TAG="v2.0.1" #performs hash check on zip file and tags the hash value to the zip fiel before sending to tc-provider.

echo -e "${GREEN}Starting IDS TOE Provider API build process...${NC}"

# Step 1: Build Docker image
echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Docker image built successfully!${NC}"
else
    echo -e "${RED}Docker image build failed!${NC}"
    exit 1
fi

# Step 2: Load image to Kubernetes cluster
echo -e "${YELLOW}Step 2: Loading Docker image to Kubernetes...${NC}"

if command -v kind &> /dev/null; then
    echo -e "${GREEN}Detected kind cluster. Loading image...${NC}"
    kind load docker-image ${IMAGE_NAME}:${IMAGE_TAG}
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Image loaded to kind successfully!${NC}"
    else
        echo -e "${RED}Failed to load image to kind!${NC}"
        exit 1
    fi
elif command -v minikube &> /dev/null; then
    echo -e "${GREEN}Detected minikube. Loading image...${NC}"
    minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Image loaded to minikube successfully!${NC}"
    else
        echo -e "${RED}Failed to load image to minikube!${NC}"
        exit 1
    fi
elif command -v k3s &> /dev/null; then
    echo -e "${GREEN}Detected K3s cluster. Importing image...${NC}"
    # Save docker image and import to K3s
    docker save ${IMAGE_NAME}:${IMAGE_TAG} | sudo k3s ctr images import -
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Image imported to K3s successfully!${NC}"
    else
        echo -e "${RED}Failed to import image to K3s!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}No local Kubernetes detected. Assuming cloud deployment.${NC}"
    echo -e "${YELLOW}Make sure to push image to registry if needed.${NC}"
fi

echo -e "${GREEN}Build process completed successfully!${NC}"
echo -e "${YELLOW}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo ""
echo -e "${YELLOW}To deploy, run: ./deploy.sh${NC}"