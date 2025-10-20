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

# Delete all configmaps except kube-root-ca.crt
echo -e "${YELLOW}Cleaning up other configmaps (preserving kube-root-ca.crt)...${NC}"
configmaps=$(kubectl get configmaps --no-headers -o custom-columns=":metadata.name" | grep -v "^kube-root-ca.crt$")

if [ -n "$configmaps" ]; then
    echo -e "${YELLOW}Found the following configmaps to delete:${NC}"
    echo "$configmaps"
    
    # Delete each configmap
    for cm in $configmaps; do
        echo -e "  Deleting configmap: ${RED}$cm${NC}"
        kubectl delete configmap "$cm" --ignore-not-found=true
        if [ $? -eq 0 ]; then
            echo -e "  ${GREEN}✓${NC} Successfully deleted $cm"
        fi
    done
else
    echo -e "${GREEN}No additional configmaps to delete${NC}"
fi

echo -e "${GREEN}Cleanup completed!${NC}"

# Show remaining configmaps
echo -e "${YELLOW}Remaining configmaps:${NC}"
kubectl get configmaps
