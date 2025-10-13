#!/bin/bash
# Cleanup Script for IDS TOE Provider API and Dependencies
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting IDS Deployment Cleanup Process...${NC}"
echo -e "${RED}WARNING: This will delete all IDS-related resources!${NC}"
echo ""

# Confirmation prompt
read -p "Are you sure you want to delete all IDS deployment resources? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]
then
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Proceeding with cleanup...${NC}"
echo ""

# Step 1: Delete IDS Connector TOE deployment
echo -e "${YELLOW}Step 1: Deleting IDS Connector TOE...${NC}"
kubectl delete -f ids_connector_toe_k8s_deployment.yml --ignore-not-found=true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}IDS Connector TOE deleted successfully!${NC}"
else
    echo -e "${RED}Error deleting IDS Connector TOE (may not exist)${NC}"
fi
echo ""

# Step 2: Delete TC Provider deployment and services
echo -e "${YELLOW}Step 2: Deleting TC Provider components...${NC}"
kubectl delete -f provider-compiled-v-0.3.yaml --ignore-not-found=true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}TC Provider components deleted successfully!${NC}"
else
    echo -e "${RED}Error deleting TC Provider components (may not exist)${NC}"
fi
echo ""

# Step 3: Delete ECC Provider ConfigMap
echo -e "${YELLOW}Step 3: Deleting ECC Provider ConfigMap...${NC}"
kubectl delete -f ecc-provider-configmap-v.2.yaml --ignore-not-found=true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}ECC Provider ConfigMap deleted successfully!${NC}"
else
    echo -e "${RED}Error deleting ECC Provider ConfigMap (may not exist)${NC}"
fi
echo ""

# Step 4: Delete BE DataApp Provider ConfigMap
echo -e "${YELLOW}Step 4: Deleting BE DataApp Provider ConfigMap...${NC}"
kubectl delete -f be-dataapp-provider-configmap.yaml --ignore-not-found=true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}BE DataApp Provider ConfigMap deleted successfully!${NC}"
else
    echo -e "${RED}Error deleting BE DataApp Provider ConfigMap (may not exist)${NC}"
fi
echo ""

# Step 5: Delete CA PEM Store
echo -e "${YELLOW}Step 5: Deleting CA PEM Store...${NC}"
kubectl delete -f ca-pemstore.yaml --ignore-not-found=true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}CA PEM Store deleted successfully!${NC}"
else
    echo -e "${RED}Error deleting CA PEM Store (may not exist)${NC}"
fi
echo ""

# Step 6: Verify cleanup
echo -e "${YELLOW}Step 6: Verifying cleanup...${NC}"
echo ""

# Check for remaining pods
echo -e "${YELLOW}Checking for remaining pods...${NC}"
REMAINING_PODS=$(kubectl get pods -l app=ids-connector-toe -o name 2>/dev/null)
REMAINING_TC_PODS=$(kubectl get pods -l io.kompose.service=tc-provider -o name 2>/dev/null)

if [ -z "$REMAINING_PODS" ] && [ -z "$REMAINING_TC_PODS" ]; then
    echo -e "${GREEN}No IDS-related pods found.${NC}"
else
    echo -e "${YELLOW}Warning: Some pods may still be terminating:${NC}"
    [ ! -z "$REMAINING_PODS" ] && echo "$REMAINING_PODS"
    [ ! -z "$REMAINING_TC_PODS" ] && echo "$REMAINING_TC_PODS"
fi

# Check for remaining services
echo ""
echo -e "${YELLOW}Checking for remaining services...${NC}"
REMAINING_SERVICES=$(kubectl get services ids-connector-toe-service tc-provider -o name 2>/dev/null)

if [ -z "$REMAINING_SERVICES" ]; then
    echo -e "${GREEN}No IDS-related services found.${NC}"
else
    echo -e "${YELLOW}Warning: Some services may still exist:${NC}"
    echo "$REMAINING_SERVICES"
fi

# Check for remaining configmaps
echo ""
echo -e "${YELLOW}Checking for remaining configmaps...${NC}"
REMAINING_CONFIGMAPS=$(kubectl get configmaps ids-connector-toe-configmap ids-connector-toe-secret ca-pemstore be-dataapp-provider-configmap ecc-provider-configmap -o name 2>/dev/null)

if [ -z "$REMAINING_CONFIGMAPS" ]; then
    echo -e "${GREEN}No IDS-related configmaps found.${NC}"
else
    echo -e "${YELLOW}Warning: Some configmaps may still exist:${NC}"
    echo "$REMAINING_CONFIGMAPS"
fi

# Check for remaining PVCs
echo ""
echo -e "${YELLOW}Checking for remaining PVCs...${NC}"
REMAINING_PVCS=$(kubectl get pvc -l io.kompose.service -o name 2>/dev/null)

if [ -z "$REMAINING_PVCS" ]; then
    echo -e "${GREEN}No IDS-related PVCs found.${NC}"
else
    echo -e "${YELLOW}Warning: Some PVCs may still exist:${NC}"
    echo "$REMAINING_PVCS"
    echo ""
    echo -e "${YELLOW}To delete these PVCs manually, run:${NC}"
    echo "kubectl delete pvc be-dataapp-provider-claim0 be-dataapp-provider-claim1 be-dataapp-provider-claim2 ecc-provider-claim0 ecc-provider-claim1"
fi

echo ""
echo -e "${GREEN}Cleanup process completed!${NC}"
echo ""
echo -e "${YELLOW}Note:${NC}"
echo "- Resources may take a few moments to fully terminate"
echo "- PVCs are not automatically deleted to prevent data loss"
echo "- To force delete stuck resources, use: kubectl delete <resource> <name> --force --grace-period=0"
echo ""