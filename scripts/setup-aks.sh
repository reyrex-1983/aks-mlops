#!/bin/bash

# MLOps AKS Setup Script
# This script sets up the complete Azure Kubernetes Service infrastructure
# Creates resources only if they don't already exist

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-mlops-rg}"
AKS_CLUSTER="${AKS_CLUSTER:-mlops-cluster}"
ACR_NAME="${ACR_NAME:-mlopsrejur2026}"
LOCATION="${LOCATION:-eastus}"
NODE_COUNT="${NODE_COUNT:-1}"
NODE_VM_SIZE="${NODE_VM_SIZE:-standard_dc4s_v3}"

echo "================================"
echo "MLOps AKS Setup Script"
echo "================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."
command -v az >/dev/null 2>&1 || { echo "❌ Azure CLI required but not installed."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl required but not installed."; exit 1; }
echo "✓ All prerequisites installed"

# Check and register resource providers
echo ""
echo "Registering Azure resource providers..."
echo "  - Microsoft.ContainerRegistry"
az provider register --namespace Microsoft.ContainerRegistry >/dev/null 2>&1 || true
echo "  - Microsoft.ContainerService"
az provider register --namespace Microsoft.ContainerService >/dev/null 2>&1 || true
echo "  - Microsoft.Storage"
az provider register --namespace Microsoft.Storage >/dev/null 2>&1 || true
echo "✓ Resource providers registered"

# Check if resource group exists
echo ""
echo "Checking resource group: $RESOURCE_GROUP"
if az group exists --name "$RESOURCE_GROUP" --query value -o tsv | grep -q "true"; then
  echo "✓ Resource group already exists: $RESOURCE_GROUP"
else
  echo "Creating resource group: $RESOURCE_GROUP"
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
  echo "✓ Resource group created"
fi

# Check if ACR exists
echo ""
echo "Checking Azure Container Registry: $ACR_NAME"
if az acr show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" >/dev/null 2>&1; then
  echo "✓ ACR already exists: $ACR_NAME"
  ACR_EXISTS=true
else
  echo "Creating Azure Container Registry: $ACR_NAME"
  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic >/dev/null
  echo "✓ ACR created successfully"
  ACR_EXISTS=false
fi

# Check if AKS cluster exists
echo ""
echo "Checking AKS cluster: $AKS_CLUSTER"
if az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" >/dev/null 2>&1; then
  echo "✓ AKS cluster already exists: $AKS_CLUSTER"
  AKS_EXISTS=true
else
  echo "Creating AKS cluster: $AKS_CLUSTER"
  echo "  - Nodes: $NODE_COUNT"
  echo "  - VM Size: $NODE_VM_SIZE"
  echo "  - Location: $LOCATION"
  echo "  (this may take 5-10 minutes)"
  
  az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-count "$NODE_COUNT" \
    --vm-set-type VirtualMachineScaleSets \
    --node-vm-size "$NODE_VM_SIZE" \
    --load-balancer-sku standard \
    --enable-managed-identity \
    --network-plugin azure \
    --generate-ssh-keys >/dev/null
  
  echo "✓ AKS cluster created successfully"
  AKS_EXISTS=false
fi

# Attach ACR to AKS (safe to run even if already attached)
echo ""
echo "Attaching ACR to AKS cluster..."
az aks update \
  -n "$AKS_CLUSTER" \
  -g "$RESOURCE_GROUP" \
  --attach-acr "$ACR_NAME" >/dev/null
echo "✓ ACR attached to AKS"

# Get cluster credentials
echo ""
echo "Getting cluster credentials..."
az aks get-credentials \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --overwrite-existing >/dev/null
echo "✓ Credentials configured for kubectl"

# Verify connection
echo ""
echo "Verifying cluster connection..."
kubectl cluster-info >/dev/null 2>&1 || { echo "❌ Failed to connect to cluster"; exit 1; }
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
echo "✓ Connected to cluster"
echo "  Nodes: $NODES"

echo ""
echo "================================"
echo "✓ AKS Setup Complete!"
echo "================================"
echo ""
echo "Configuration Summary:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  AKS Cluster: $AKS_CLUSTER"
echo "  Container Registry: $ACR_NAME"
echo "  Location: $LOCATION"
echo "  Node Count: $NODE_COUNT"
echo "  VM Size: $NODE_VM_SIZE"
echo ""
echo "Next steps:"
echo "1. Build and push Docker images:"
echo "   export ACR_NAME=$ACR_NAME"
echo "   az acr login --name \$ACR_NAME"
echo "   docker build -f Dockerfile.training -t \${ACR_NAME}.azurecr.io/mlops-training:latest ."
echo "   docker build -f Dockerfile.serving -t \${ACR_NAME}.azurecr.io/mlops-serving:latest ."
echo "   docker push \${ACR_NAME}.azurecr.io/mlops-training:latest"
echo "   docker push \${ACR_NAME}.azurecr.io/mlops-serving:latest"
echo ""
echo "2. Deploy to AKS:"
echo "   export ACR_NAME=$ACR_NAME"
echo "   bash scripts/deploy.sh"
echo ""
