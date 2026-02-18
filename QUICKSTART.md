# MLOps Quick Reference

## 🚀 Quick Start Commands

```bash
# Setup Azure & AKS
az group create --name mlops-rg --location eastus
az aks create --resource-group mlops-rg --name mlops-cluster --node-count 3
az aks get-credentials --resource-group mlops-rg --name mlops-cluster

# Build & Push Images
az acr login --name mlopsregistry
docker build -f Dockerfile.training -t mlopsregistry.azurecr.io/mlops-training:latest .
docker push mlopsregistry.azurecr.io/mlops-training:latest

# Deploy
sed -i 's/<REGISTRY>/mlopsregistry.azurecr.io/g' deployment/*.yaml
kubectl apply -f deployment/namespace.yaml
kubectl apply -f deployment/rbac.yaml
kubectl apply -f deployment/storage.yaml
kubectl apply -f deployment/training.yaml
kubectl apply -f deployment/serving.yaml
```

## 📊 Monitoring

```bash
# Check status
kubectl get pods -n mlops
kubectl get svc -n mlops
kubectl top pods -n mlops

# View logs
kubectl logs -f -n mlops deployment/model-serving
kubectl logs -f -n mlops job/model-training-job

# Port forward
kubectl port-forward -n mlops svc/model-serving-service 8000:8000
```

## 🧪 Testing

```bash
SERVICE_IP=$(kubectl get svc model-serving-service -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Health check
curl http://$SERVICE_IP:8000/health

# Predict
curl -X POST http://$SERVICE_IP:8000/predict -H "Content-Type: application/json" -d '{
  "customer_age": 45, "transaction_hour": 14, "product_price": 99.99,
  "cart_value": 250.00, "session_duration": 450, "items_in_cart": 3,
  "pages_visited": 8, "discount_applied": 1, "is_weekend": 0,
  "day_of_week": 3, "month": 2, "product_category": "Electronics",
  "device_type": "Mobile"
}'
```

## 🔧 Debugging

```bash
# Describe pod
kubectl describe pod -n mlops <pod-name>

# Execute command in pod
kubectl exec -it -n mlops <pod-name> -- /bin/bash

# Check model files
kubectl exec -it -n mlops <pod-name> -- ls -la /app/models
```

## 🗑️ Cleanup

```bash
kubectl delete namespace mlops
az group delete --name mlops-rg
```

## 📁 Project Structure

```
├── data/              # Data generation
├── training/          # Model training
├── serving/           # FastAPI app
├── deployment/        # K8s manifests
├── monitoring/        # Prometheus, Jaeger
├── scripts/           # Helper scripts
├── .github/workflows/ # CI/CD
├── Dockerfile.*       # Container images
└── README.md          # Full docs
```

## 🎯 Key Endpoints

- Health: `GET /health`
- Predict: `POST /predict`
- Model Info: `GET /model/info`
- Metrics: `GET /metrics` (Prometheus)

**See README.md for complete documentation**
