# MLOps on Azure Kubernetes Service (AKS)

A production-ready MLOps pipeline for e-commerce purchase prediction using Azure Kubernetes Service. Features automated model training, FastAPI serving, Prometheus monitoring, and GitHub Actions CI/CD.

## Architecture

```
Data Pipeline → Model Training → Model Registry
                                      ↓
                          Model Serving (FastAPI)
                          - /predict endpoint
                          - /health checks
                          - /metrics (Prometheus)
                          ↓
                    Kubernetes Services
                    - Horizontal scaling (HPA)
                    - Load balancing
                    - Health monitoring
                    ↓
                    Monitoring Stack
                    - Prometheus metrics
                    - Alert rules
                    - Distributed tracing (Jaeger)
```

## Key Components

### 1. Data Generation & Training
- **generate_data.py**: Creates synthetic e-commerce transaction data
- **train.py**: Trains Random Forest classifier for purchase prediction
- **Models**: Saved to persistent volume for serving pods to access

### 2. Model Serving
- **FastAPI application** with endpoints:
  - `POST /predict` - Make predictions
  - `GET /health` - Health check
  - `GET /metrics` - Prometheus metrics
  - `GET /model/info` - Model metadata
- **Auto-scaling**: HPA scales 3-10 replicas based on CPU/memory

### 3. Kubernetes Deployment
- **Namespace isolation**: All resources in `mlops` namespace
- **RBAC**: Proper service accounts and permissions
- **Persistent Volumes**: For shared model storage
- **Network Policies**: Security-focused traffic rules

### 4. CI/CD Pipeline
- **GitHub Actions**: Build Docker images on push
- **Azure Container Registry**: Store container images
- **Automated deployment**: Deploy to AKS on merge to main

### 5. Monitoring & Observability
- **Prometheus**: Metrics collection and alerting
- **Jaeger**: Distributed tracing
- **Health checks**: Liveness and readiness probes
- **Logs**: Structured logging from all components

## Project Structure

```
aks-mlops/
├── data/                    # Data generation
│   ├── generate_data.py
│   ├── train_data.csv
│   └── test_data.csv
├── training/                # Model training
│   ├── train.py
│   ├── models/             # Trained models (git-ignored)
│   └── requirements.txt
├── serving/                 # FastAPI serving
│   ├── app.py
│   ├── requirements.txt
│   └── tests/
├── deployment/              # Kubernetes manifests
│   ├── namespace.yaml
│   ├── rbac.yaml
│   ├── storage.yaml
│   ├── training.yaml
│   ├── serving.yaml
│   └── ingress.yaml
├── monitoring/              # Observability
│   ├── prometheus.yaml
│   ├── logging.yaml
│   └── tracing.yaml
├── scripts/                 # Helper scripts
│   ├── setup-aks.sh
│   ├── deploy.sh
│   ├── test-inference.sh
│   └── cleanup.sh
├── .github/workflows/       # CI/CD pipelines
│   ├── build.yml
│   └── deploy.yml
├── Dockerfile.training
├── Dockerfile.serving
├── README.md               # This file
├── QUICKSTART.md           # Quick reference
└── requirements-dev.txt
```

## Quick Start

### Prerequisites
```bash
# Install Azure CLI
brew install azure-cli

# Install kubectl
brew install kubectl

# Install Docker Desktop
# Download from https://www.docker.com/products/docker-desktop
```

### Setup (5-10 minutes)

```bash
# 1. Set Azure subscription
az account set --subscription <SUBSCRIPTION_ID>

# 2. Create resource group
az group create --name mlops-rg --location eastus

# 3. Create AKS cluster
az aks create \
  --resource-group mlops-rg \
  --name mlops-cluster \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --enable-managed-identity

# 4. Get credentials
az aks get-credentials --resource-group mlops-rg --name mlops-cluster
```

### Build & Push Images

```bash
# Create container registry
az acr create --resource-group mlops-rg --name mlopsregistry --sku Basic

# Build and push images
az acr login --name mlopsregistry

docker build -f Dockerfile.training -t mlopsregistry.azurecr.io/mlops-training:latest .
docker push mlopsregistry.azurecr.io/mlops-training:latest

docker build -f Dockerfile.serving -t mlopsregistry.azurecr.io/mlops-serving:latest .
docker push mlopsregistry.azurecr.io/mlops-serving:latest
```

### Deploy to AKS

```bash
# Update image references
sed -i 's/<REGISTRY>/mlopsregistry.azurecr.io/g' deployment/*.yaml

# Deploy
kubectl apply -f deployment/namespace.yaml
kubectl apply -f deployment/rbac.yaml
kubectl apply -f deployment/storage.yaml
kubectl apply -f deployment/training.yaml
kubectl apply -f deployment/serving.yaml
kubectl apply -f deployment/ingress.yaml

# Monitor deployment
kubectl get pods -n mlops -w
kubectl logs -f -n mlops job/model-training-job
```

## Using the API

```bash
# Get service endpoint
SERVICE_IP=$(kubectl get svc model-serving-service -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Health check
curl http://$SERVICE_IP:8000/health

# Make prediction
curl -X POST http://$SERVICE_IP:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "customer_age": 45,
    "transaction_hour": 14,
    "product_price": 99.99,
    "cart_value": 250.00,
    "session_duration": 450,
    "items_in_cart": 3,
    "pages_visited": 8,
    "discount_applied": 1,
    "is_weekend": 0,
    "day_of_week": 3,
    "month": 2,
    "product_category": "Electronics",
    "device_type": "Mobile"
  }'

# Get model info
curl http://$SERVICE_IP:8000/model/info

# Get metrics
curl http://$SERVICE_IP:8000/metrics
```

## Local Development

```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r training/requirements.txt

# Generate training data
python data/generate_data.py

# Train model locally
python training/train.py

# Run serving app
cd serving
pip install -r requirements.txt
uvicorn app:app --reload

# In another terminal, test the API
curl http://localhost:8000/health
```

## Monitoring

### View Metrics
```bash
# Check pods
kubectl get pods -n mlops

# Check services
kubectl get svc -n mlops

# Pod resource usage
kubectl top pods -n mlops

# View logs
kubectl logs -f -n mlops deployment/model-serving

# Describe pod
kubectl describe pod -n mlops <pod-name>
```

### Access Prometheus
```bash
kubectl port-forward -n mlops svc/prometheus 9090:9090
# Open http://localhost:9090
```

## Model Training

The project includes:
- **One-time training**: `kubectl apply -f deployment/training.yaml`
- **Scheduled retraining**: CronJob runs weekly (edit schedule in training.yaml)
- **Model versioning**: Each model saved with timestamp
- **Automatic pickup**: Serving pods use latest model

## Scaling

### Horizontal Pod Autoscaler (HPA)
```bash
# View HPA status
kubectl get hpa -n mlops

# Adjust scaling (edit deployment/serving.yaml)
minReplicas: 3
maxReplicas: 10
cpu threshold: 70%
memory threshold: 80%
```

### Manual scaling
```bash
kubectl scale deployment model-serving -n mlops --replicas=5
```

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete namespace mlops

# Delete AKS cluster
az aks delete --resource-group mlops-rg --name mlops-cluster

# Delete resource group (everything)
az group delete --name mlops-rg
```

## CI/CD Setup

1. **GitHub Secrets** (set in your repo):
   - `ACR_USERNAME`: Container registry username
   - `ACR_PASSWORD`: Container registry password
   - `AZURE_CREDENTIALS`: Full Azure credentials JSON

2. **Workflows** (auto-triggered):
   - `.github/workflows/build.yml`: Build on push
   - `.github/workflows/deploy.yml`: Deploy on merge to main

## Production Checklist

- [ ] Configure TLS certificates (cert-manager)
- [ ] Set up monitoring alerts (email/Slack)
- [ ] Enable Azure Policy for governance
- [ ] Configure persistent volume backups
- [ ] Set up log aggregation (ELK/Application Insights)
- [ ] Document runbooks
- [ ] Test disaster recovery
- [ ] Set up cost monitoring
- [ ] Configure resource quotas
- [ ] Enable pod security policies

## Troubleshooting

### Model not loading
```bash
# Check PVC is mounted
kubectl exec -it -n mlops <pod-name> -- ls -la /app/models

# Check permissions
kubectl exec -it -n mlops <pod-name> -- chmod 644 /app/models/*
```

### Pod not starting
```bash
# Check events
kubectl describe pod -n mlops <pod-name>

# View logs
kubectl logs -f -n mlops <pod-name>

# Previous logs
kubectl logs -n mlops <pod-name> --previous
```

### LoadBalancer IP pending
```bash
# Wait for external IP (can take a few minutes)
kubectl get svc -n mlops -w

# Or port-forward temporarily
kubectl port-forward -n mlops svc/model-serving-service 8000:8000
```

## Performance Targets

- **Prediction Latency (p95)**: <100ms
- **Throughput**: 100+ req/sec per pod
- **Availability**: >99.9% uptime
- **Model Accuracy**: ~82%
- **Training Time**: 2-5 minutes

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | Azure AKS |
| ML Framework | scikit-learn |
| Model | Random Forest Classifier |
| API | FastAPI + Uvicorn |
| Metrics | Prometheus |
| Tracing | Jaeger |
| Logging | Fluent Bit |
| Ingress | NGINX |
| CI/CD | GitHub Actions |
| IaC | Kubernetes YAML |

## Resources

- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Guide](https://prometheus.io/docs/introduction/overview/)

## License

MIT License - Use freely for learning and production

## Support

For issues or questions, please open an issue in the GitHub repository.

---

**Built with ❤️ for MLOps on Azure**
**Last Updated: February 2026**
