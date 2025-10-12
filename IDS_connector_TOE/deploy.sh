#!/bin/bash

# Deploy Script for IDS TOE Provider API

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="ids-connector-toe"
IMAGE_TAG="latest"

echo -e "${GREEN}Starting IDS TOE Provider API deployment process...${NC}"

# Step 1: Apply Kubernetes manifests
echo -e "${YELLOW}Step 1: Applying Kubernetes manifests...${NC}"
kubectl apply -f ids_connector_toe_k8s_deployment.yml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Kubernetes resources created successfully!${NC}"
else
    echo -e "${RED}Failed to create Kubernetes resources!${NC}"
    exit 1
fi

# Step 2: Wait for deployment to be ready
echo -e "${YELLOW}Step 2: Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/ids-connector-toe-deployment

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment is ready!${NC}"
else
    echo -e "${RED}Deployment failed to become ready!${NC}"
    echo -e "${YELLOW}Checking pod status...${NC}"
    kubectl get pods -l app=ids-connector-toe
    echo -e "${YELLOW}Checking recent events...${NC}"
    kubectl get events --sort-by=.metadata.creationTimestamp | tail -10
    exit 1
fi

# Step 3: Show deployment status
echo -e "${YELLOW}Step 3: Deployment Status:${NC}"
kubectl get pods -l app=ids-connector-toe
kubectl get service ids-connector-toe-service

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}To access the service:${NC}"
echo "  - Within cluster: http://ids-connector-toe-service:8005"
echo "  - Port forward: kubectl port-forward service/ids-connector-toe-service 8005:8005"
echo ""
echo -e "${YELLOW}To check logs:${NC}"
echo "  kubectl logs -f deployment/ids-connector-toe-deployment"
echo ""
echo -e "${YELLOW}API Endpoints:${NC}"
echo "  - POST /api/IDSconnector/post_data - Post data to tc-provider:8090"
echo "  - GET  /health - Health check"
echo "  - GET  /api/IDSconnector/TOE/info - Provider information"
echo "  - POST /api/IDSconnector/clear-cache - Clear catalog cache"
echo ""

# Ask if user wants to start port forwarding
read -p "Do you want to start port forwarding now to access the API? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${GREEN}Starting port forwarding...${NC}"
    echo -e "${YELLOW}Access the API documentation at: http://localhost:8005/docs${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
    kubectl port-forward service/ids-connector-toe-service 8005:8005
fi