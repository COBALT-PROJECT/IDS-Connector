#!/bin/bash

# Quick Redeploy Script - Restarts the deployment with existing image

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Redeploying IDS Connector SDT...${NC}"

# Restart the deployment (forces new pod creation with same image)
echo -e "${YELLOW}Restarting deployment...${NC}"
kubectl rollout restart deployment/ids-connector-sdt-deployment

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment restart initiated!${NC}"
else
    echo -e "${RED}Failed to restart deployment!${NC}"
    exit 1
fi

# Wait for rollout to complete
echo -e "${YELLOW}Waiting for rollout to complete...${NC}"
kubectl rollout status deployment/ids-connector-sdt-deployment --timeout=300s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Rollout completed successfully!${NC}"
else
    echo -e "${RED}Rollout failed!${NC}"
    exit 1
fi

# Show status
echo ""
kubectl get pods -l app=ids-connector-sdt
echo ""
echo -e "${GREEN}Redeployment completed!${NC}"