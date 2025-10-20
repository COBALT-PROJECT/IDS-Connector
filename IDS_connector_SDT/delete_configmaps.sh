#!/bin/bash

# Script to delete all configmaps except kube-root-ca.crt

echo "Fetching all configmaps..."

# Get all configmap names except the header line and kube-root-ca.crt
configmaps=$(kubectl get configmaps --no-headers -o custom-columns=":metadata.name" | grep -v "^kube-root-ca.crt$")

# Check if there are any configmaps to delete
if [ -z "$configmaps" ]; then
    echo "No configmaps to delete (only kube-root-ca.crt exists or no configmaps found)"
    exit 0
fi

echo "The following configmaps will be deleted:"
echo "$configmaps"
echo ""

# Ask for confirmation
read -p "Are you sure you want to delete these configmaps? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Delete each configmap
    for cm in $configmaps; do
        echo "Deleting configmap: $cm"
        kubectl delete configmap "$cm"
        if [ $? -eq 0 ]; then
            echo "  ✓ Successfully deleted $cm"
        else
            echo "  ✗ Failed to delete $cm"
        fi
    done
    echo ""
    echo "Deletion complete!"
else
    echo "Deletion cancelled."
fi

# Show remaining configmaps
echo ""
echo "Remaining configmaps:"
kubectl get configmaps