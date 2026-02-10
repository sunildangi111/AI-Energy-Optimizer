#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train RandomForest on realistic Walmart energy data
"""

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib, os
import numpy as np
import pandas as pd
from download_real_data import prepare_real_data

def train_and_save(model_path="backend/models/real_rf_model.pkl"):
    """Train model on realistic data and save"""
    
    # Prepare the real data
    X_train, X_test, y_train, y_test = prepare_real_data("real_walmart_energy.csv")
    
    print("\n=== Training RandomForest on Real Data ===")
    
    # Create and train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1  # Use all CPU cores
    )
    
    model.fit(X_train, y_train)
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    
    # Print results
    print(f"\n📊 Model Performance:")
    print(f"   MAE:  {mae:.2f} kW")
    print(f"   RMSE: {rmse:.2f} kW")
    print(f"   R²:   {r2:.3f}")
    
    # Feature importance
    feature_names = ['hour', 'temperature', 'occupancy', 'is_weekend']
    importances = model.feature_importances_
    
    print(f"\n🔍 Feature Importance:")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
        print(f"   {name:12}: {imp:.3f}")
    
    # Save model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"\n✅ Model saved to {model_path}")
    
    # Show sample predictions
    print(f"\n📈 Sample Predictions (vs Actual):")
    sample_indices = np.random.choice(len(y_test), 5, replace=False)
    for i in sample_indices:
        actual = y_test.iloc[i]
        predicted = y_pred[i]
        hour = X_test.iloc[i]['hour']
        temp = X_test.iloc[i]['temperature']
        occ = X_test.iloc[i]['occupancy']
        weekend = X_test.iloc[i]['is_weekend']
        
        print(f"   Hour {int(hour):2d}, {float(temp):5.1f}°F, {float(occ):3.0f} people, weekend={bool(weekend)}: "
              f"{float(predicted):6.1f} kW (actual: {float(actual):6.1f} kW)")
    
    return model

if __name__ == "__main__":
    train_and_save()
