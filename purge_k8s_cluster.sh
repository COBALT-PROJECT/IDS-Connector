#!/bin/bash

# Script to delete all Kubernetes resources in a namespace
# Usage: ./delete-k8s-namespace-resources.sh [namespace]
# If no namespace is provided, it will use 'default'

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get namespace from argument or use default
NAMESPACE="${1:-default}"

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}Kubernetes Resource Deletion Script${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if the namespace exists
if !  kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}Error: Namespace '$NAMESPACE' does not exist${NC}"
    exit 1
fi

echo -e "${YELLOW}Target Namespace: ${GREEN}$NAMESPACE${NC}"
echo ""

# Confirmation prompt
echo -e "${RED}WARNING: This will delete ALL resources in the '$NAMESPACE' namespace! ${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Operation cancelled. ${NC}"
    exit 0
fi

echo -e "${GREEN}Starting resource deletion...${NC}"
echo ""

# Define resource types to delete (in order)
# Some resources should be deleted before others to avoid hanging
RESOURCE_TYPES=(
    "all"                    # Covers pods, services, deployments, replicasets, statefulsets, daemonsets, jobs, cronjobs
    "ingress"
    "configmap"
    "secret"
    "serviceaccount"
    "persistentvolumeclaim"
    "horizontalpodautoscaler"
    "verticalpodautoscaler"
    "networkpolicy"
    "poddisruptionbudget"
    "limitrange"
    "resourcequota"
    "rolebinding"
    "role"
    "endpoints"
    "endpointslice"
    "event"
    "lease"
)

# Function to delete resources
delete_resources() {
    local resource_type=$1
    echo -e "${YELLOW}Deleting ${resource_type}...${NC}"
    
    # Check if any resources exist
    if kubectl get "$resource_type" -n "$NAMESPACE" 2>/dev/null | grep -q .; then
        kubectl delete "$resource_type" --all -n "$NAMESPACE" --grace-period=0 --force 2>/dev/null || true
        echo -e "${GREEN}✓ Deleted ${resource_type}${NC}"
    else
        echo -e "${YELLOW}  No ${resource_type} found${NC}"
    fi
    echo ""
}

# Delete each resource type
for resource in "${RESOURCE_TYPES[@]}"; do
    delete_resources "$resource"
done

# Additional cleanup for any remaining resources
echo -e "${YELLOW}Performing final cleanup...${NC}"
kubectl delete all --all -n "$NAMESPACE" --grace-period=0 --force 2>/dev/null || true

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Resource deletion completed! ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Show remaining resources (if any)
echo -e "${YELLOW}Checking for any remaining resources...${NC}"
remaining=$(kubectl get all -n "$NAMESPACE" 2>/dev/null | tail -n +2 | wc -l)

if [ "$remaining" -eq 0 ]; then
    echo -e "${GREEN}✓ All resources have been successfully deleted from namespace '$NAMESPACE'${NC}"
else
    echo -e "${YELLOW}⚠ Some resources may still be terminating: ${NC}"
    kubectl get all -n "$NAMESPACE"
    echo ""
    echo -e "${YELLOW}Note: Some resources may take time to fully terminate. ${NC}"
fi

echo ""
echo -e "${YELLOW}Note: The namespace '$NAMESPACE' itself has NOT been deleted. ${NC}"
echo -e "${YELLOW}To delete the namespace, run: kubectl delete namespace $NAMESPACE${NC}"