"""
FastAPI application for serving the ML model with inference endpoint.
Includes health checks, metrics, and logging.
"""

import os
import logging
import joblib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import uvicorn


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
prediction_counter = Counter(
    'predictions_total',
    'Total number of predictions',
    ['model_version', 'prediction']
)

prediction_duration = Histogram(
    'prediction_duration_seconds',
    'Time spent making predictions'
)

model_load_counter = Counter(
    'model_loads_total',
    'Total number of model loads'
)


class PredictionRequest(BaseModel):
    """Input schema for prediction requests."""
    customer_age: int = Field(..., ge=18, le=100)
    transaction_hour: int = Field(..., ge=0, le=23)
    product_price: float = Field(..., gt=0)
    cart_value: float = Field(..., gt=0)
    session_duration: int = Field(..., gt=0)
    items_in_cart: int = Field(..., ge=0)
    pages_visited: int = Field(..., ge=0)
    discount_applied: int = Field(..., ge=0, le=1)
    is_weekend: int = Field(..., ge=0, le=1)
    day_of_week: int = Field(..., ge=0, le=6)
    month: int = Field(..., ge=1, le=12)
    product_category: str = Field(..., regex="^(Electronics|Fashion|Home|Sports|Beauty)$")
    device_type: str = Field(..., regex="^(Mobile|Desktop|Tablet)$")


class PredictionResponse(BaseModel):
    """Output schema for predictions."""
    prediction: int
    confidence: float
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    version: str
    timestamp: str


class ModelServer:
    """ML Model Server."""
    
    def __init__(self, model_dir='./models'):
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.encoders = None
        self.metadata = None
        self.model_version = None
        self.load_model()
    
    def load_model(self):
        """Load the latest model and preprocessors."""
        try:
            # Find the latest model files
            model_files = sorted(self.model_dir.glob('model_*.pkl'))
            if not model_files:
                raise FileNotFoundError("No model files found")
            
            latest_model = model_files[-1]
            version = latest_model.stem.replace('model_', '')
            
            self.model = joblib.load(latest_model)
            self.scaler = joblib.load(self.model_dir / f'scaler_{version}.pkl')
            self.encoders = joblib.load(self.model_dir / f'encoders_{version}.pkl')
            
            # Load metadata
            import json
            with open(self.model_dir / f'metadata_{version}.json') as f:
                self.metadata = json.load(f)
            
            self.model_version = version
            model_load_counter.labels().inc()
            logger.info(f"Model {version} loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict(self, features: Dict) -> Dict:
        """Make a prediction."""
        with prediction_duration.time():
            try:
                # Prepare features array
                feature_names = ['customer_age', 'transaction_hour', 'product_price', 'cart_value',
                               'session_duration', 'items_in_cart', 'pages_visited', 'discount_applied',
                               'is_weekend', 'day_of_week', 'month', 'product_category', 'device_type']
                
                # Encode categorical features
                features_processed = features.copy()
                for cat_col in ['product_category', 'device_type']:
                    features_processed[cat_col] = self.encoders[cat_col].transform([features[cat_col]])[0]
                
                # Create array in correct order
                X = np.array([features_processed[name] for name in feature_names]).reshape(1, -1)
                
                # Scale numerical features (skip last 2 which are categorical already encoded)
                numerical_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                X_scaled = X.copy().astype(float)
                X_scaled[:, numerical_indices] = self.scaler.transform(X[:, numerical_indices].astype(float))
                
                # Make prediction
                prediction = self.model.predict(X_scaled)[0]
                confidence = float(self.model.predict_proba(X_scaled)[0][prediction])
                
                prediction_counter.labels(
                    model_version=self.model_version,
                    prediction=int(prediction)
                ).inc()
                
                return {
                    'prediction': int(prediction),
                    'confidence': confidence,
                    'model_version': self.model_version,
                    'timestamp': datetime.now().isoformat()
                }
            
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                raise


# Initialize FastAPI app
app = FastAPI(
    title="E-Commerce Purchase Prediction API",
    description="MLOps model serving for purchase prediction",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model server
model_server = None


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup."""
    global model_server
    try:
        model_server = ModelServer(model_dir=os.environ.get('MODEL_DIR', './models'))
        logger.info("Model server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize model server: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if model_server and model_server.model else "unhealthy",
        model_loaded=model_server is not None and model_server.model is not None,
        version=model_server.model_version if model_server else "unknown",
        timestamp=datetime.now().isoformat()
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make a prediction with the model."""
    if not model_server or not model_server.model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model server not ready"
        )
    
    try:
        result = model_server.predict(request.dict())
        return PredictionResponse(**result)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/model/info")
async def model_info():
    """Get model information."""
    if not model_server or not model_server.metadata:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    return {
        "model_version": model_server.model_version,
        "model_type": model_server.metadata.get('model_type'),
        "metrics": model_server.metadata.get('metrics'),
        "feature_count": model_server.metadata.get('feature_count'),
        "feature_names": model_server.metadata.get('feature_names')
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="info"
    )
