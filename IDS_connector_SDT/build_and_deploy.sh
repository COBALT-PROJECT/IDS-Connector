#!/bin/bash

# Build and Deploy Script for IDS Consumer API

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="ids-connector-sdt"
IMAGE_TAG="latest"

echo -e "${GREEN}Starting IDS Consumer API deployment process...${NC}"

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
elif command -v minikube &> /dev/null; then
    echo -e "${GREEN}Detected minikube. Loading image...${NC}"
    minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
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

# Step 3: Apply Kubernetes manifests
echo -e "${YELLOW}Step 3: Applying Kubernetes manifests...${NC}"
kubectl apply -f ids_connector_sdt_k8s_deployment.yml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Kubernetes resources created successfully!${NC}"
else
    echo -e "${RED}Failed to create Kubernetes resources!${NC}"
    exit 1
fi

# Step 4: Wait for deployment to be ready
echo -e "${YELLOW}Step 4: Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/ids-connector-sdt-deployment

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment is ready!${NC}"
else
    echo -e "${RED}Deployment failed to become ready!${NC}"
    exit 1
fi

# Step 5: Show deployment status
echo -e "${YELLOW}Step 5: Deployment Status:${NC}"
kubectl get pods -l app=ids-connector-sdt
kubectl get service ids-connector-sdt-service

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}To access the service:${NC}"
echo "  - Within cluster: http://ids-connector-sdt-service:8004"
echo "  - Port forward: kubectl port-forward service/ids-connector-sdt-service 8004:8004"
echo ""
echo -e "${YELLOW}To check logs:${NC}"
echo "  kubectl logs -f deployment/ids-connector-sdt-deployment"
echo ""

# Ask if user wants to start port forwarding
read -p "Do you want to start port forwarding now to access the GUI? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${GREEN}Starting port forwarding...${NC}"
    echo -e "${YELLOW}Access the API documentation at: http://localhost:8004/docs${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
    kubectl port-forward service/ids-connector-sdt-service 8004:8004
fi