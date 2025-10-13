#!/bin/bash
# Deploy Script for IDS TOE Provider API with Dependencies
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Complete IDS Deployment Process...${NC}"
echo ""

# Step 1: Deploy CA PEM Store (Certificates)
echo -e "${YELLOW}Step 1: Deploying CA PEM Store (Certificates)...${NC}"
kubectl apply -f ca-pemstore.yaml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}CA PEM Store deployed successfully!${NC}"
else
    echo -e "${RED}Failed to deploy CA PEM Store!${NC}"
    exit 1
fi
echo ""

# Step 2: Deploy BE DataApp Provider ConfigMap
echo -e "${YELLOW}Step 2: Deploying BE DataApp Provider ConfigMap...${NC}"
kubectl apply -f be-dataapp-provider-configmap.yaml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}BE DataApp Provider ConfigMap deployed successfully!${NC}"
else
    echo -e "${RED}Failed to deploy BE DataApp Provider ConfigMap!${NC}"
    exit 1
fi
echo ""

# Step 3: Deploy ECC Provider ConfigMap
echo -e "${YELLOW}Step 3: Deploying ECC Provider ConfigMap...${NC}"
kubectl apply -f ecc-provider-configmap-v.2.yaml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}ECC Provider ConfigMap deployed successfully!${NC}"
else
    echo -e "${RED}Failed to deploy ECC Provider ConfigMap!${NC}"
    exit 1
fi
echo ""

# Step 4: Deploy Provider Components (Main TC Provider)
echo -e "${YELLOW}Step 4: Deploying TC Provider Components...${NC}"
kubectl apply -f provider-compiled-v-0.3.yaml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}TC Provider components deployed successfully!${NC}"
else
    echo -e "${RED}Failed to deploy TC Provider components!${NC}"
    exit 1
fi
echo ""

# Step 5: Wait for TC Provider deployment to be ready
echo -e "${YELLOW}Step 5: Waiting for TC Provider deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/tc-provider
if [ $? -eq 0 ]; then
    echo -e "${GREEN}TC Provider deployment is ready!${NC}"
else
    echo -e "${RED}TC Provider deployment failed to become ready!${NC}"
    echo -e "${YELLOW}Checking TC Provider pod status...${NC}"
    kubectl get pods -l io.kompose.service=tc-provider
    echo -e "${YELLOW}Checking recent events...${NC}"
    kubectl get events --sort-by=.metadata.creationTimestamp | tail -10
    exit 1
fi
echo ""

# Step 6: Deploy IDS Connector TOE
echo -e "${YELLOW}Step 6: Deploying IDS Connector TOE...${NC}"
kubectl apply -f ids_connector_toe_k8s_deployment.yml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}IDS Connector TOE deployed successfully!${NC}"
else
    echo -e "${RED}Failed to deploy IDS Connector TOE!${NC}"
    exit 1
fi
echo ""

# Step 7: Wait for IDS Connector TOE deployment to be ready
echo -e "${YELLOW}Step 7: Waiting for IDS Connector TOE deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/ids-connector-toe-deployment
if [ $? -eq 0 ]; then
    echo -e "${GREEN}IDS Connector TOE deployment is ready!${NC}"
else
    echo -e "${RED}IDS Connector TOE deployment failed to become ready!${NC}"
    echo -e "${YELLOW}Checking IDS Connector TOE pod status...${NC}"
    kubectl get pods -l app=ids-connector-toe
    echo -e "${YELLOW}Checking recent events...${NC}"
    kubectl get events --sort-by=.metadata.creationTimestamp | tail -10
    exit 1
fi
echo ""

# Step 8: Show deployment status
echo -e "${YELLOW}Step 8: Overall Deployment Status:${NC}"
echo ""
echo -e "${GREEN}TC Provider Status:${NC}"
kubectl get pods -l io.kompose.service=tc-provider
kubectl get service tc-provider
echo ""
echo -e "${GREEN}IDS Connector TOE Status:${NC}"
kubectl get pods -l app=ids-connector-toe
kubectl get service ids-connector-toe-service
echo ""

echo -e "${GREEN}Complete deployment finished successfully!${NC}"
echo ""
echo -e "${YELLOW}Service Access Information:${NC}"
echo "  TC Provider:"
echo "    - Within cluster: http://tc-provider:8090 (ECC)"
echo "    - Within cluster: http://tc-provider:8083 (BE DataApp)"
echo ""
echo "  IDS Connector TOE:"
echo "    - Within cluster: http://ids-connector-toe-service:8005"
echo "    - Port forward: kubectl port-forward service/ids-connector-toe-service 8005:8005"
echo ""
echo -e "${YELLOW}To check logs:${NC}"
echo "  TC Provider logs:"
echo "    kubectl logs -f deployment/tc-provider -c ecc-provider"
echo "    kubectl logs -f deployment/tc-provider -c be-dataapp-provider"
echo "  IDS Connector TOE logs:"
echo "    kubectl logs -f deployment/ids-connector-toe-deployment"
echo ""
echo -e "${YELLOW}API Endpoints:${NC}"
echo "  - POST /api/IDSconnector/post_data - Post data to tc-provider:8090"
echo "  - GET  /health - Health check"
echo "  - GET  /api/IDSconnector/TOE/info - Provider information"
echo "  - POST /api/IDSconnector/clear-cache - Clear catalog cache"
echo ""

# Ask if user wants to start port forwarding
read -p "Do you want to start port forwarding for IDS Connector TOE to access the API? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${GREEN}Starting port forwarding...${NC}"
    echo -e "${YELLOW}Access the API documentation at: http://localhost:8005/docs${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop port forwarding${NC}"
    kubectl port-forward service/ids-connector-toe-service 8005:8005
fi