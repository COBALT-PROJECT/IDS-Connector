#!/bin/bash

# Cleanup Script - Remove failed deployments and start fresh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleaning up existing IDS Connector SDT resources...${NC}"

# Delete Kubernetes resources
echo -e "${YELLOW}Deleting Kubernetes resources...${NC}"
kubectl delete deployment ids-connector-sdt-deployment --ignore-not-found=true
kubectl delete service ids-connector-sdt-service --ignore-not-found=true
kubectl delete configmap ids-connector-sdt-configmap --ignore-not-found=true
kubectl delete secret ids-connector-sdt-secret --ignore-not-found=true

echo -e "${GREEN}Cleanup completed!${NC}"

# Check if we should redeploy
read -p "Do you want to redeploy now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${GREEN}Starting fresh deployment...${NC}"
    
    # Import image to K3s first
    echo -e "${YELLOW}Importing Docker image to K3s...${NC}"
    docker save ids-connector-sdt:latest | sudo k3s ctr images import -
    
    # Apply manifests
    echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"
    kubectl apply -f kubernetes-deployment.yaml
    
    # Wait for deployment
    echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
    kubectl rollout status deployment/ids-connector-sdt-deployment --timeout=300s
    
    # Show status
    echo -e "${GREEN}Deployment status:${NC}"
    kubectl get pods -l app=ids-connector-sdt
    kubectl get pods ids-connector-sdt-pod
else
    echo -e "${YELLOW}Cleanup only - no redeployment${NC}"
fi