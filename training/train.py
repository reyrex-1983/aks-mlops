"""
Model training pipeline for e-commerce purchase prediction.
Trains a random forest model and saves to model registry.
"""

import os
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score, classification_report
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


class MLPipeline:
    def __init__(self, data_dir='../data', model_dir='./models'):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.model = None
        self.model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def load_data(self):
        """Load training and test data."""
        print("Loading data...")
        train_df = pd.read_csv(self.data_dir / 'train_data.csv')
        test_df = pd.read_csv(self.data_dir / 'test_data.csv')
        
        print(f"Training data shape: {train_df.shape}")
        print(f"Test data shape: {test_df.shape}")
        
        return train_df, test_df
    
    def preprocess_data(self, df, fit_encoders=False):
        """Preprocess features and target."""
        df = df.copy()
        
        # Separate features and target
        X = df.drop('will_purchase', axis=1)
        y = df['will_purchase']
        
        # Convert timestamp to datetime features
        X['timestamp'] = pd.to_datetime(X['timestamp'])
        X['day_of_week'] = X['timestamp'].dt.dayofweek
        X['month'] = X['timestamp'].dt.month
        X = X.drop('timestamp', axis=1)
        
        # Encode categorical features
        categorical_cols = X.select_dtypes(include='object').columns
        for col in categorical_cols:
            if fit_encoders:
                encoder = LabelEncoder()
                X[col] = encoder.fit_transform(X[col])
                self.label_encoders[col] = encoder
            else:
                X[col] = self.label_encoders[col].transform(X[col])
        
        # Scale numerical features
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        if fit_encoders:
            X[numerical_cols] = self.scaler.fit_transform(X[numerical_cols])
        else:
            X[numerical_cols] = self.scaler.transform(X[numerical_cols])
        
        return X, y
    
    def train(self, X_train, y_train):
        """Train the model."""
        print("\nTraining Random Forest model...")
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
        
        self.model.fit(X_train, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)
        print(f"Cross-validation scores: {cv_scores}")
        print(f"Mean CV score: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        return self.model
    
    def evaluate(self, X_test, y_test):
        """Evaluate model on test data."""
        print("\nEvaluating model on test set...")
        
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
        }
        
        print("\nModel Performance:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.4f}")
        
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['No Purchase', 'Purchase']))
        
        return metrics
    
    def save_model(self, metrics):
        """Save model and metadata."""
        model_path = self.model_dir / f'model_{self.model_version}.pkl'
        scaler_path = self.model_dir / f'scaler_{self.model_version}.pkl'
        encoders_path = self.model_dir / f'encoders_{self.model_version}.pkl'
        metadata_path = self.model_dir / f'metadata_{self.model_version}.json'
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        joblib.dump(self.label_encoders, encoders_path)
        
        metadata = {
            'model_version': self.model_version,
            'timestamp': datetime.now().isoformat(),
            'model_type': 'RandomForestClassifier',
            'n_estimators': 100,
            'metrics': metrics,
            'feature_count': self.model.n_features_in_,
            'feature_names': ['customer_age', 'transaction_hour', 'product_price', 'cart_value',
                            'session_duration', 'items_in_cart', 'pages_visited', 'discount_applied',
                            'is_weekend', 'day_of_week', 'month', 'product_category', 'device_type']
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Model saved to {model_path}")
        print(f"✓ Scaler saved to {scaler_path}")
        print(f"✓ Encoders saved to {encoders_path}")
        print(f"✓ Metadata saved to {metadata_path}")
        
        return model_path, metadata


def main():
    print("=" * 60)
    print("E-Commerce Purchase Prediction Model Training Pipeline")
    print("=" * 60)
    
    pipeline = MLPipeline()
    
    # Load data
    train_df, test_df = pipeline.load_data()
    
    # Preprocess
    X_train, y_train = pipeline.preprocess_data(train_df, fit_encoders=True)
    X_test, y_test = pipeline.preprocess_data(test_df, fit_encoders=False)
    
    print(f"\nPreprocessed training data shape: {X_train.shape}")
    print(f"Preprocessed test data shape: {X_test.shape}")
    
    # Train
    pipeline.train(X_train, y_train)
    
    # Evaluate
    metrics = pipeline.evaluate(X_test, y_test)
    
    # Save
    pipeline.save_model(metrics)
    
    print("\n" + "=" * 60)
    print("Training pipeline completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
