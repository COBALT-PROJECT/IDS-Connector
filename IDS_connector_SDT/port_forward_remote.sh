#!/bin/bash

# Remote Port Forwarding Script for IDS Connector SDT
# Allows access from remote machines to the API

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
echo -e "${GREEN}   IDS Connector SDT Remote Port Forwarding${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Check if service exists
kubectl get service ${SERVICE_NAME} &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Service ${SERVICE_NAME} not found!${NC}"
    echo -e "${YELLOW}Please deploy the application first using ./deploy.sh${NC}"
    exit 1
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}Service found!${NC}"
echo ""
echo -e "${BLUE}Starting port forwarding on all interfaces${NC}"
echo -e "${BLUE}Local IP: ${SERVER_IP}${NC}"
echo ""
echo -e "${YELLOW}Access points from remote machines:${NC}"
echo -e "  📚 API Documentation: ${GREEN}http://${SERVER_IP}:${LOCAL_PORT}/docs${NC}"
echo -e "  🔧 Alternative API Docs: ${GREEN}http://${SERVER_IP}:${LOCAL_PORT}/redoc${NC}"
echo -e "  ❤️  Health Check: ${GREEN}http://${SERVER_IP}:${LOCAL_PORT}/health${NC}"
echo -e "  🔍 Consumer Info: ${GREEN}http://${SERVER_IP}:${LOCAL_PORT}/api/IDSconnector/SDT/info${NC}"
echo ""
echo -e "${YELLOW}Local access points:${NC}"
echo -e "  📚 API Documentation: ${GREEN}http://localhost:${LOCAL_PORT}/docs${NC}"
echo ""
echo -e "${RED}Note: Make sure firewall allows port ${LOCAL_PORT}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Start port forwarding on all interfaces
kubectl port-forward --address 0.0.0.0 service/${SERVICE_NAME} ${LOCAL_PORT}:${POD_PORT}