#!/bin/bash

# MLOps Test Inference Script
# Tests the deployed model serving API

set -e

NAMESPACE="mlops"
SERVICE_NAME="model-serving-service"
PORT=8000

echo "================================"
echo "MLOps Test Inference Script"
echo "================================"
echo ""

# Get service endpoint
echo "Getting service endpoint..."
SERVICE_IP=$(kubectl get svc $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -z "$SERVICE_IP" ]; then
  echo "⚠️  LoadBalancer IP not available yet. Trying port-forward..."
  kubectl port-forward svc/$SERVICE_NAME $PORT:$PORT -n $NAMESPACE &
  PF_PID=$!
  sleep 2
  SERVICE_IP="localhost"
  echo "Using port-forward with PID: $PF_PID"
fi

ENDPOINT="http://$SERVICE_IP:$PORT"
echo "Service Endpoint: $ENDPOINT"
echo ""

# Test health endpoint
echo "Testing health endpoint..."
if curl -s -f "$ENDPOINT/health" > /dev/null; then
  echo "✓ Health check passed"
else
  echo "❌ Health check failed"
  exit 1
fi

echo ""
echo "Testing inference endpoint..."

# Create test request
TEST_REQUEST='{
  "customer_age": 35,
  "customer_tenure_months": 24,
  "cart_value": 150.50,
  "product_count": 5,
  "category": "electronics",
  "device_type": "mobile",
  "time_of_day": "afternoon"
}'

# Send prediction request
RESPONSE=$(curl -s -X POST \
  "$ENDPOINT/predict" \
  -H "Content-Type: application/json" \
  -d "$TEST_REQUEST")

echo "Request:"
echo "$TEST_REQUEST" | python3 -m json.tool

echo ""
echo "Response:"
echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "================================"
echo "✓ Test Inference Complete!"
echo "================================"

# Cleanup port-forward if used
if [ ! -z "$PF_PID" ]; then
  kill $PF_PID
fi
