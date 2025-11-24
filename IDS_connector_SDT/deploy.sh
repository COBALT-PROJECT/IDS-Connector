#!/bin/bash
# Deploy Script for IDS Consumer API (Image already built)
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
# Configuration
IMAGE_NAME="ids-connector-sdt"
IMAGE_TAG="v2.0.2"

# YAML files to deploy in order
YAML_FILES=(
    "ca-pemstore.yaml"
    "be-dataapp-consumer-configmap.yaml"
    "ecc-consumer-configmap-v.2.yaml"
    "consumer-compiled-v-0.3.yaml"
    "ids_connector_sdt_k8s_deployment.yml"
    "pods_sync_k3s.yml"
)

echo -e "${GREEN}Starting IDS Connector SDT deployment...${NC}"
# Step 1: Load image to Kubernetes cluster
echo -e "${YELLOW}Step 1: Loading image to Kubernetes...${NC}"
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
fi
# Step 2: Apply Kubernetes manifests in order
echo -e "${YELLOW}Step 2: Applying Kubernetes manifests in order...${NC}"
for yaml_file in "${YAML_FILES[@]}"; do
    echo -e "${GREEN}Applying ${yaml_file}...${NC}"
    kubectl apply -f ${yaml_file}
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ ${yaml_file} applied successfully${NC}"
    else
        echo -e "${RED}✗ Failed to apply ${yaml_file}${NC}"
        exit 1
    fi
    # Small delay between deployments to allow resources to initialize
    sleep 2
done
echo -e "${GREEN}All Kubernetes resources created/updated successfully!${NC}"

# Step 3: Wait for deployment to be ready
echo -e "${YELLOW}Step 3: Waiting for deployment to be ready...${NC}"
kubectl rollout status deployment/ids-connector-sdt-deployment --timeout=300s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment is ready!${NC}"
else
    echo -e "${RED}Deployment failed to become ready!${NC}"
    exit 1
fi
# Step 4: Show deployment status
echo -e "${YELLOW}Step 4: Deployment Status:${NC}"
echo ""
kubectl get pods -l app=ids-connector-sdt
echo ""
kubectl get service ids-connector-sdt-service
echo ""
# Step 5: Show access information
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Access Information:${NC}"
echo "  - Within cluster: http://ids-connector-sdt-service:8004"
echo "  - Port forward: kubectl port-forward service/ids-connector-sdt-service 8004:8004"
echo "  - Health check: curl http://localhost:8004/health (after port-forward)"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  - Check logs: kubectl logs -f deployment/ids-connector-sdt-deployment"
echo "  - Restart pod: kubectl rollout restart deployment/ids-connector-sdt-deployment"
echo "  - Scale deployment: kubectl scale deployment/ids-connector-sdt-deployment --replicas=2"
echo "  - Delete all resources: for file in ${YAML_FILES[*]}; do kubectl delete -f \$file; done"
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