#!/bin/bash
# Cleanup Script - Remove all deployed resources
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# YAML files to delete (in reverse order of deployment)
YAML_FILES=(
    "pods_sync_k3s.yml"
    "ids_connector_sdt_k8s_deployment.yml"
    "consumer-compiled-v-0.3.yaml"
    "ecc-consumer-configmap-v.2.yaml"
    "be-dataapp-consumer-configmap.yaml"
    "ca-pemstore.yaml"
)

echo -e "${YELLOW}Cleaning up all IDS Connector and related resources...${NC}"

# Method 1: Delete using YAML files (if they exist)
echo -e "${YELLOW}Method 1: Attempting to delete using YAML files...${NC}"
files_found=false
for yaml_file in "${YAML_FILES[@]}"; do
    if [ -f "$yaml_file" ]; then
        files_found=true
        echo -e "${YELLOW}Deleting resources from ${yaml_file}...${NC}"
        kubectl delete -f ${yaml_file} --ignore-not-found=true
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Deleted resources from ${yaml_file}${NC}"
        else
            echo -e "${RED}✗ Failed to delete some resources from ${yaml_file}${NC}"
        fi
    else
        echo -e "${YELLOW}File ${yaml_file} not found, skipping...${NC}"
    fi
done

if [ "$files_found" = false ]; then
    echo -e "${YELLOW}No YAML files found. Using direct resource deletion...${NC}"
fi

# Method 2: Direct deletion of known resources (fallback)
echo -e "${YELLOW}Method 2: Direct deletion of specific resources...${NC}"

# Delete IDS Connector SDT resources
echo -e "${YELLOW}Deleting IDS Connector SDT resources...${NC}"
kubectl delete deployment ids-connector-sdt-deployment --ignore-not-found=true
kubectl delete service ids-connector-sdt-service --ignore-not-found=true
kubectl delete configmap ids-connector-sdt-configmap --ignore-not-found=true
kubectl delete secret ids-connector-sdt-secret --ignore-not-found=true

# Delete consumer resources (likely from consumer-compiled-v-0.3.yaml)
echo -e "${YELLOW}Deleting consumer resources...${NC}"
kubectl delete deployment tc-consumer --ignore-not-found=true
kubectl delete service tc-consumer --ignore-not-found=true

# Delete ECC consumer configmap
echo -e "${YELLOW}Deleting ECC consumer configmap...${NC}"
kubectl delete configmap ecc-consumer-configmap --ignore-not-found=true

# Delete BE data app consumer configmap
echo -e "${YELLOW}Deleting BE data app consumer configmap...${NC}"
kubectl delete configmap be-dataapp-consumer-configmap --ignore-not-found=true

# Delete CA pemstore (could be configmap or secret)
echo -e "${YELLOW}Deleting CA pemstore resources...${NC}"
kubectl delete configmap ca-pemstore --ignore-not-found=true
kubectl delete secret ca-pemstore --ignore-not-found=true

# Delete any pods sync resources (if any)
echo -e "${YELLOW}Deleting pods sync resources...${NC}"
kubectl delete daemonset pods-sync --ignore-not-found=true
kubectl delete deployment pods-sync --ignore-not-found=true

# Clean up any remaining configmaps (optional - preserving kube-root-ca.crt)
echo -e "${YELLOW}Checking for any remaining project configmaps...${NC}"
configmaps=$(kubectl get configmaps --no-headers -o custom-columns=":metadata.name" | grep -v "^kube-root-ca.crt$" | grep -E "(ids-|consumer-|ecc-|be-dataapp-|ca-pemstore)")
if [ -n "$configmaps" ]; then
    echo -e "${YELLOW}Found the following project configmaps to delete:${NC}"
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
    echo -e "${GREEN}No additional project configmaps to delete${NC}"
fi

echo -e "${GREEN}Cleanup completed!${NC}"

# Show remaining resources
echo -e "${YELLOW}Remaining resources check:${NC}"
echo -e "${YELLOW}Deployments:${NC}"
kubectl get deployments
echo -e "${YELLOW}Services:${NC}"
kubectl get services
echo -e "${YELLOW}ConfigMaps:${NC}"
kubectl get configmaps
echo -e "${YELLOW}Secrets:${NC}"
kubectl get secrets | grep -v "default-token"