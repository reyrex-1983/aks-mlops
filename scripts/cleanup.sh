#!/bin/bash

# MLOps Cleanup Script
# Removes all Azure and Kubernetes resources

set -e

RESOURCE_GROUP="${RESOURCE_GROUP:-mlops-rg}"
AKS_CLUSTER="${AKS_CLUSTER:-mlops-cluster}"

echo "================================"
echo "MLOps Cleanup Script"
echo "================================"
echo ""
echo "⚠️  WARNING: This will delete all resources!"
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "AKS Cluster: $AKS_CLUSTER"
echo ""
read -p "Are you sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Cleanup cancelled."
  exit 0
fi

# Delete Kubernetes resources first
echo ""
echo "Deleting Kubernetes namespace..."
kubectl delete namespace mlops --ignore-not-found=true

echo "Waiting for namespace deletion..."
sleep 10

# Delete AKS cluster
echo ""
echo "Deleting AKS cluster (this may take 5-10 minutes)..."
az aks delete \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --yes

# Delete resource group
echo ""
echo "Deleting resource group (this will delete all associated resources)..."
az group delete \
  --name "$RESOURCE_GROUP" \
  --yes

echo ""
echo "================================"
echo "✓ Cleanup Complete!"
echo "================================"
echo ""
echo "All resources have been deleted."
