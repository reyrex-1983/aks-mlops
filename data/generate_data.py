"""
Generate synthetic e-commerce transaction dataset for ML model training.
This simulates real-world sales prediction scenario.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path


def generate_ecommerce_data(n_samples=10000, seed=42):
    """Generate synthetic e-commerce transaction data."""
    np.random.seed(seed)
    
    # Generate dates
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=x) for x in np.random.randint(0, 730, n_samples)]
    
    # Generate features
    data = {
        'timestamp': dates,
        'customer_age': np.random.normal(40, 15, n_samples).astype(int).clip(18, 80),
        'product_category': np.random.choice(['Electronics', 'Fashion', 'Home', 'Sports', 'Beauty'], n_samples),
        'transaction_hour': np.random.randint(0, 24, n_samples),
        'device_type': np.random.choice(['Mobile', 'Desktop', 'Tablet'], n_samples),
        'is_weekend': np.random.binomial(1, 0.3, n_samples),
        'product_price': np.random.lognormal(3.5, 1.2, n_samples),
        'cart_value': np.random.gamma(50, 2, n_samples),
        'session_duration': np.random.exponential(120, n_samples).astype(int).clip(10, 3600),
        'items_in_cart': np.random.poisson(3, n_samples),
        'pages_visited': np.random.poisson(5, n_samples),
        'discount_applied': np.random.binomial(1, 0.2, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Generate target variable (purchase likelihood)
    # More complex relationship to simulate real patterns
    df['will_purchase'] = (
        (0.3 * (df['cart_value'] > df['cart_value'].median())) +
        (0.2 * (df['session_duration'] > 300)) +
        (0.15 * (df['discount_applied'] == 1)) +
        (0.15 * (df['customer_age'] > 35)) +
        (0.1 * (df['items_in_cart'] > 2)) +
        (0.1 * np.random.random(n_samples))
    )
    df['will_purchase'] = (df['will_purchase'] > 0.5).astype(int)
    
    return df


def main():
    print("Generating synthetic e-commerce dataset...")
    
    # Generate training and test data
    train_df = generate_ecommerce_data(n_samples=8000, seed=42)
    test_df = generate_ecommerce_data(n_samples=2000, seed=43)
    
    # Create data directory if it doesn't exist
    data_dir = Path(__file__).parent
    
    # Save as CSV
    train_df.to_csv(data_dir / 'train_data.csv', index=False)
    test_df.to_csv(data_dir / 'test_data.csv', index=False)
    
    print(f"✓ Generated {len(train_df)} training samples")
    print(f"✓ Generated {len(test_df)} test samples")
    print(f"✓ Features: {list(train_df.columns[:-1])}")
    print(f"✓ Target variable: 'will_purchase' (binary)")
    print(f"✓ Class distribution: {dict(train_df['will_purchase'].value_counts())}")
    print(f"\nData saved to {data_dir}/")


if __name__ == '__main__':
    main()
