#!/bin/bash

# Port Forwarding Script for IDS Connector SDT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="ids-connector-sdt-service"
LOCAL_PORT=8004
POD_PORT=8004

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}     IDS Connector SDT Port Forwarding${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Check if service exists
kubectl get service ${SERVICE_NAME} &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Service ${SERVICE_NAME} not found!${NC}"
    echo -e "${YELLOW}Please deploy the application first using ./deploy.sh${NC}"
    exit 1
fi

# Check if deployment is ready
READY_REPLICAS=$(kubectl get deployment ids-connector-sdt-deployment -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
if [ -z "$READY_REPLICAS" ] || [ "$READY_REPLICAS" == "0" ]; then
    echo -e "${RED}Error: No ready pods found for ids-connector-sdt-deployment${NC}"
    echo -e "${YELLOW}Please check pod status with: kubectl get pods${NC}"
    exit 1
fi

echo -e "${GREEN}Service found and pods are ready!${NC}"
echo ""
echo -e "${BLUE}Starting port forwarding from localhost:${LOCAL_PORT} to ${SERVICE_NAME}:${POD_PORT}${NC}"
echo ""
echo -e "${YELLOW}Access points:${NC}"
echo -e "  📚 API Documentation: ${GREEN}http://localhost:${LOCAL_PORT}/docs${NC}"
echo -e "  🔧 Alternative API Docs: ${GREEN}http://localhost:${LOCAL_PORT}/redoc${NC}"
echo -e "  ❤️  Health Check: ${GREEN}http://localhost:${LOCAL_PORT}/health${NC}"
echo -e "  🔍 Consumer Info: ${GREEN}http://localhost:${LOCAL_PORT}/api/IDSconnector/SDT/info${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Start port forwarding
kubectl port-forward service/${SERVICE_NAME} ${LOCAL_PORT}:${POD_PORT}