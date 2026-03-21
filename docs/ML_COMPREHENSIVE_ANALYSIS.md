# Fazri Analyzer - Comprehensive ML Component Analysis

**Analysis Date:** 2026-03-15
**Analyst:** AI Engineer Agent
**Project:** Fazri Analyzer - Entity Tracking & Anomaly Detection System

---

## Executive Summary

The Fazri Analyzer employs machine learning for location prediction and anomaly detection across campus entity tracking data. The system currently has **31 trained Random Forest models** (14.7 MB total) for individual entity location prediction, plus rule-based anomaly detection services.

**Key Findings:**
- ✅ Well-structured ML prediction service with explainability features
- ⚠️ No model versioning or A/B testing infrastructure
- ⚠️ Models loaded synchronously on-demand (potential latency issues)
- ⚠️ No GPU utilization or inference optimization
- ⚠️ Limited MLOps infrastructure (no drift detection, monitoring, or automated retraining)
- ⚠️ Anomaly detection relies on rule-based heuristics rather than ML

---

## 1. Model Architecture Review

### 1.1 ML Models Inventory

**Location:** `/Users/dinokage/dev/fazri-analyzer/backend/models/`

**Total Models:** 31 pickle files (`.pkl`)
**Total Size:** ~14.7 MB
**Naming Convention:** `predictor_<ENTITY_ID>.pkl`

**Model Size Distribution:**
```
Smallest: 185 KB (predictor_E103820.pkl)
Largest:  928 KB (predictor_E100403.pkl)
Average:  ~474 KB per model
```

**Model Type:** RandomForestClassifier (scikit-learn)

**Model Structure (per entity):**
```python
{
    'model': RandomForestClassifier,
    'location_encoder': LabelEncoder,
    'event_encoder': LabelEncoder,
    'feature_importance': dict
}
```

### 1.2 ML Prediction Service Architecture

**File:** `/Users/dinokage/dev/fazri-analyzer/backend/services/ml_predictor.py`

**Class:** `LocationPredictor`

**Algorithm:** Random Forest Classifier
- **n_estimators:** 100 trees
- **max_depth:** 10
- **random_state:** 42 (reproducibility)

**Features Engineered (5 features):**
1. `hour` - Hour of day (0-23)
2. `day_of_week` - Day of week (0-6)
3. `prev_location_encoded` - Previous location (label encoded)
4. `prev_event_type_encoded` - Previous event type (label encoded)
5. `time_since_last` - Hours since last event (continuous)

**Target Variable:** Next location (categorical, label encoded)

**Training Requirements:**
- Minimum samples: 10 events per entity
- Sequential data required for temporal feature extraction

**Prediction Output:**
```python
{
    'target_time': str,
    'predictions': [
        {
            'location': str,
            'confidence': float,  # 0.0-1.0
            'explanation': {
                'confidence_level': str,  # 'high'|'medium'|'low'
                'evidence': List[str],
                'key_factors': List[str],
                'reasoning': str
            }
        }
    ],
    'method': str,  # 'random_forest_ml' | 'rule_based_fallback'
    'model_info': dict
}
```

### 1.3 Anomaly Detection Services

#### System-Level Anomaly Detection
**File:** `/Users/dinokage/dev/fazri-analyzer/backend/services/anomaly_detection.py`

**Detection Methods:** Rule-based (no ML)
- Overcrowding detection (capacity threshold violations)
- Underutilization detection (< 20% capacity during peak hours)
- Data integrity checks (null timestamps, negative occupancy)
- Negative flow detection (exits > entries)

**Severity Levels:** CRITICAL | HIGH | MEDIUM | LOW

#### Entity-Level Anomaly Detection
**File:** `/Users/dinokage/dev/fazri-analyzer/backend/services/entity_anomaly_detection.py`

**Detection Methods:** Rule-based (12 anomaly types)
1. Off-hours access violations
2. Role-based access violations
3. Department-based access violations
4. Impossible travel detection (< 2 min between distant zones)
5. Multi-modal location mismatches (card vs WiFi)
6. Curfew violations (hostel entry/exit after 23:00)
7. Excessive access frequency (> 10 swipes/hour)
8. Booking no-shows
9. Entry without exit (tailgating detection)
10. Exit without entry (piggybacking detection)
11. Abnormal dwell time (zone-specific thresholds)
12. Consecutive same-direction swipes (card sharing detection)

**Data Sources:** Neo4j graph database queries

---

## 2. Training & Inference Pipeline Analysis

### 2.1 Model Training Pipeline

**Training Script:** `/Users/dinokage/dev/fazri-analyzer/backend/scripts/train_predictor.py`

**Workflow:**
```
1. Query Neo4j for entities with ≥10 events
2. For each entity:
   a. Fetch event timeline
   b. Initialize LocationPredictor
   c. Train model with cross-validation
   d. Save model as .pkl file
3. Report training metrics
```

**Training Metrics Tracked:**
- Training samples count
- Unique locations learned
- Feature importance scores

**Critical Gaps:**
- ❌ No train/validation/test split
- ❌ No cross-validation reported
- ❌ No model performance metrics (accuracy, F1, precision, recall)
- ❌ No hyperparameter tuning
- ❌ No automated retraining schedule
- ❌ No data versioning

### 2.2 Inference Pipeline

**API Endpoint:** `/api/v1/graph/predict/location/{entity_id}`

**Inference Flow:**
```
1. Load model from disk (.pkl file)
2. Extract features from recent events
3. Encode categorical features
4. Predict with Random Forest
5. Generate explanations
6. Return top-K predictions
```

**Inference Modes:**
- **ML Mode:** Random Forest prediction (when model exists)
- **Fallback Mode:** Rule-based (hourly patterns or last known location)

**Performance Characteristics:**
- Model loading: On-demand (not preloaded)
- Inference latency: Not measured
- Memory usage: Not monitored
- No caching mechanism

### 2.3 Batch Processing

**Current State:** ❌ No batch processing infrastructure

**Observations:**
- All predictions are synchronous/on-demand
- No batch inference for gap-filling
- No pre-computed predictions stored

---

## 3. Performance Analysis

### 3.1 Model Loading & Initialization

**Current Implementation:**
```python
# On-demand loading (no caching)
predictor = LocationPredictor()
predictor.load_model(model_path)  # Disk I/O on every request
```

**Issues:**
- ❌ Cold start latency for each prediction request
- ❌ Repeated disk I/O for same entity
- ❌ No model warm-up or preloading
- ❌ No in-memory model cache (e.g., LRU cache)

**Estimated Impact:**
- Disk I/O: ~50-100ms per model load (474 KB average)
- Memory overhead: 14.7 MB if all models cached
- Recommendation: Implement LRU cache for frequently accessed models

### 3.2 Inference Latency

**Current State:** Not measured or monitored

**Theoretical Analysis:**
```
Total Latency = Model Loading + Feature Extraction + Inference + Explanation

Estimated breakdown:
- Model loading: 50-100ms (disk I/O)
- Feature extraction: 10-20ms (database query + pandas ops)
- Random Forest inference: 5-10ms (100 trees, max_depth=10)
- Explanation generation: 20-30ms (historical pattern analysis)

Total: ~85-160ms per prediction (without caching)
With caching: ~35-60ms
```

**SLA Target:** < 100ms for real-time applications

**Recommendations:**
- Add `@lru_cache` for model loading
- Pre-compute feature statistics
- Batch database queries
- Add latency instrumentation

### 3.3 Memory Usage

**Model Memory Footprint:**
- Single model: ~474 KB average
- All 31 models: 14.7 MB
- Random Forest overhead: Minimal (tree-based, not dense)

**Current State:** Not monitored

**Recommendations:**
- Monitor memory with `psutil` or Prometheus
- Implement model cache eviction policy
- Set memory limits per container
- Profile memory leaks in long-running processes

### 3.4 GPU Utilization

**Current State:** ❌ Not applicable

**Analysis:**
- RandomForestClassifier runs on CPU only
- No GPU-accelerated inference (TensorFlow/PyTorch not used for predictions)
- Scikit-learn does not support GPU

**Recommendations:**
- For current models: Stay with CPU (appropriate for Random Forest)
- For future deep learning models: Use TensorFlow/PyTorch with GPU support
- Consider GPU for batch processing if scaling to thousands of entities

---

## 4. Code Quality Analysis

### 4.1 Feature Engineering

**Strengths:**
✅ Clear temporal features (hour, day_of_week)
✅ Sequential context (previous location, event type)
✅ Time-based features (time_since_last)

**Weaknesses:**
- ⚠️ No feature scaling/normalization
- ⚠️ No feature importance threshold for selection
- ⚠️ Missing location embeddings or proximity features
- ⚠️ No cyclic encoding for hour/day (sin/cos transformation)
- ⚠️ No interaction features (e.g., hour × location)

**Recommendations:**
```python
# Example: Cyclic encoding for hour
import numpy as np

def encode_cyclic_time(hour):
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    return hour_sin, hour_cos
```

### 4.2 Data Preprocessing Pipeline

**Current Implementation:**
```python
# Extract features inline during training
for i in range(1, len(df)):
    curr_row = df.iloc[i]
    prev_row = df.iloc[i-1]
    # ... feature extraction
```

**Issues:**
- ❌ No reusable preprocessing pipeline
- ❌ Feature extraction duplicated between training and inference
- ❌ No data validation (missing values, outliers)
- ❌ No feature versioning

**Recommendations:**
```python
# Example: Use sklearn Pipeline
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

pipeline = Pipeline([
    ('feature_extractor', FeatureTransformer()),
    ('scaler', StandardScaler()),
    ('model', RandomForestClassifier())
])
```

### 4.3 Model Evaluation Metrics

**Current State:** ❌ No evaluation metrics tracked

**Missing Metrics:**
- Accuracy, Precision, Recall, F1-score
- Confusion matrix
- Per-location class performance
- Calibration curves (confidence reliability)

**Recommendations:**
```python
from sklearn.metrics import classification_report, confusion_matrix

# After training
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
```

### 4.4 ML Code Organization

**Strengths:**
✅ Separation of concerns (LocationPredictor class)
✅ Clear method responsibilities
✅ Explainability features built-in

**Weaknesses:**
- ⚠️ No abstract base class for predictors
- ⚠️ Feature extraction tightly coupled to predictor
- ⚠️ No configuration management (hyperparameters hardcoded)
- ⚠️ No logging/monitoring integration

**Recommendations:**
```python
# Example: Config management
from pydantic import BaseModel

class ModelConfig(BaseModel):
    n_estimators: int = 100
    max_depth: int = 10
    min_samples_split: int = 2
    random_state: int = 42

config = ModelConfig()
model = RandomForestClassifier(**config.dict())
```

---

## 5. MLOps Analysis

### 5.1 Model Deployment Strategy

**Current Strategy:** File-based pickle storage

**Strengths:**
✅ Simple to implement
✅ Fast for small models

**Weaknesses:**
- ❌ No model versioning
- ❌ No rollback capability
- ❌ No A/B testing support
- ❌ No canary deployments
- ❌ No model registry (e.g., MLflow)

**Recommendations:**
```python
# Example: MLflow integration
import mlflow

with mlflow.start_run():
    mlflow.log_params({"n_estimators": 100, "max_depth": 10})
    mlflow.log_metrics({"accuracy": 0.85, "f1": 0.82})
    mlflow.sklearn.log_model(model, "location_predictor")
```

### 5.2 Model Monitoring & Drift Detection

**Current State:** ❌ No monitoring infrastructure

**Missing Components:**
- Model prediction logging
- Feature distribution tracking
- Prediction confidence monitoring
- Concept drift detection
- Data drift detection

**Recommendations:**
```python
# Example: Drift detection with Evidently
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=train_df, current_data=recent_df)
report.save_html("drift_report.html")
```

### 5.3 A/B Testing Capabilities

**Current State:** ❌ No A/B testing framework

**Recommendations:**
1. Implement multi-armed bandit for model selection
2. Track model performance by version
3. Gradual rollout with traffic splitting
4. Statistical significance testing

**Example Architecture:**
```python
class ModelRouter:
    def __init__(self):
        self.models = {
            "v1": load_model("v1.pkl"),
            "v2": load_model("v2.pkl")
        }
        self.traffic_split = {"v1": 0.5, "v2": 0.5}

    def predict(self, features):
        model_version = self._select_model()
        return self.models[model_version].predict(features)
```

### 5.4 Model Retraining Pipeline

**Current State:** Manual retraining only

**Missing Components:**
- ❌ Automated retraining triggers
- ❌ Performance degradation detection
- ❌ Scheduled retraining (daily/weekly)
- ❌ Incremental learning support
- ❌ Retraining data selection logic

**Recommendations:**
```python
# Example: Automated retraining trigger
from datetime import datetime, timedelta

class ModelRetrainingScheduler:
    def should_retrain(self, model_metadata):
        # Trigger conditions
        days_since_training = (datetime.now() - model_metadata['trained_at']).days
        accuracy_drop = model_metadata['current_accuracy'] < 0.8

        return days_since_training > 7 or accuracy_drop
```

---

## 6. Specific Recommendations

### 6.1 Model Optimization

#### Recommendation 1: Model Compression
```python
# Reduce Random Forest size while maintaining accuracy
from sklearn.ensemble import RandomForestClassifier

# Current
model = RandomForestClassifier(n_estimators=100, max_depth=10)

# Optimized
model = RandomForestClassifier(
    n_estimators=50,      # Reduce trees (100 → 50)
    max_depth=8,          # Reduce depth (10 → 8)
    min_samples_leaf=5,   # Increase min leaf samples
    n_jobs=-1             # Parallelize training
)

# Expected: ~50% model size reduction, <5% accuracy loss
```

#### Recommendation 2: Quantization
```python
# Convert model to lighter format (not applicable to sklearn)
# Alternative: Use LightGBM or XGBoost for smaller models

from lightgbm import LGBMClassifier

model = LGBMClassifier(
    n_estimators=50,
    max_depth=8,
    num_leaves=31
)
# Expected: 60-70% size reduction vs Random Forest
```

#### Recommendation 3: Feature Pruning
```python
# Remove low-importance features
def select_top_features(feature_importance, threshold=0.05):
    important_features = {
        feat: imp for feat, imp in feature_importance.items()
        if imp > threshold
    }
    return list(important_features.keys())

# Apply before training
selected_features = select_top_features(feature_importance)
X_train = X_train[selected_features]
```

### 6.2 Inference Optimization

#### Recommendation 1: Model Caching with LRU
```python
from functools import lru_cache
from pathlib import Path
import pickle

class CachedModelLoader:
    @lru_cache(maxsize=10)  # Cache 10 most recent models
    def load_model(self, model_path: str):
        with open(model_path, 'rb') as f:
            return pickle.load(f)

    def get_predictor(self, entity_id: str):
        model_path = f"models/predictor_{entity_id}.pkl"
        return self.load_model(model_path)

# Expected: 50-100ms latency reduction on cache hits
```

#### Recommendation 2: Batch Prediction API
```python
from fastapi import APIRouter
from typing import List

@router.post("/api/v1/predict/batch")
async def batch_predict(entity_ids: List[str], target_time: str):
    """Batch prediction for multiple entities"""
    predictions = {}

    # Load models in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(predict_location, eid, target_time): eid
            for eid in entity_ids
        }

        for future in as_completed(futures):
            entity_id = futures[future]
            predictions[entity_id] = future.result()

    return predictions

# Expected: 3-5x throughput improvement for batch requests
```

#### Recommendation 3: Async Prediction Pipeline
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncLocationPredictor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def predict_async(self, entity_id: str, target_time: datetime):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._predict_sync,
            entity_id,
            target_time
        )

    def _predict_sync(self, entity_id: str, target_time: datetime):
        # Existing synchronous prediction logic
        pass
```

### 6.3 Code Refactoring for Better ML Practices

#### Recommendation 1: Separate Feature Engineering
```python
# File: backend/services/ml/feature_engineering.py

from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

@dataclass
class LocationFeatures:
    hour: int
    day_of_week: int
    prev_location_encoded: int
    prev_event_type_encoded: int
    time_since_last: float

    # New features
    hour_sin: float = None
    hour_cos: float = None
    is_weekend: bool = False
    is_peak_hour: bool = False

class FeatureEngineer:
    def __init__(self, location_encoder, event_encoder):
        self.location_encoder = location_encoder
        self.event_encoder = event_encoder

    def extract_features(self, events: List[Dict]) -> pd.DataFrame:
        """Reusable feature extraction for training and inference"""
        features = []

        for i in range(1, len(events)):
            curr = events[i]
            prev = events[i-1]

            hour = curr['timestamp'].hour
            day_of_week = curr['timestamp'].weekday()

            # Cyclic encoding
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)

            # Boolean features
            is_weekend = day_of_week >= 5
            is_peak_hour = hour in [9, 10, 11, 14, 15, 16, 17]

            features.append(LocationFeatures(
                hour=hour,
                day_of_week=day_of_week,
                prev_location_encoded=self.location_encoder.transform([prev['location']])[0],
                prev_event_type_encoded=self.event_encoder.transform([prev['event_type']])[0],
                time_since_last=(curr['timestamp'] - prev['timestamp']).total_seconds() / 3600,
                hour_sin=hour_sin,
                hour_cos=hour_cos,
                is_weekend=is_weekend,
                is_peak_hour=is_peak_hour
            ))

        return pd.DataFrame([f.__dict__ for f in features])
```

#### Recommendation 2: Model Registry with MLflow
```python
# File: backend/services/ml/model_registry.py

import mlflow
from mlflow.tracking import MlflowClient

class ModelRegistry:
    def __init__(self, tracking_uri: str = "sqlite:///mlflow.db"):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()

    def register_model(self, model, entity_id: str, metrics: Dict):
        with mlflow.start_run(run_name=f"predictor_{entity_id}"):
            # Log parameters
            mlflow.log_params({
                "entity_id": entity_id,
                "model_type": "RandomForest",
                "n_estimators": model.n_estimators,
                "max_depth": model.max_depth
            })

            # Log metrics
            mlflow.log_metrics(metrics)

            # Log model
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=f"location_predictor_{entity_id}"
            )

    def load_latest_model(self, entity_id: str):
        model_name = f"location_predictor_{entity_id}"
        model_uri = f"models:/{model_name}/latest"
        return mlflow.sklearn.load_model(model_uri)

    def get_model_version(self, entity_id: str, version: int):
        model_name = f"location_predictor_{entity_id}"
        model_uri = f"models:/{model_name}/{version}"
        return mlflow.sklearn.load_model(model_uri)
```

#### Recommendation 3: Monitoring & Logging
```python
# File: backend/services/ml/monitoring.py

from datetime import datetime
from typing import Dict, Any
import logging
from prometheus_client import Counter, Histogram

# Prometheus metrics
prediction_counter = Counter(
    'ml_predictions_total',
    'Total ML predictions',
    ['entity_id', 'model_version', 'method']
)

prediction_latency = Histogram(
    'ml_prediction_latency_seconds',
    'ML prediction latency',
    ['entity_id', 'model_version']
)

class PredictionLogger:
    def __init__(self):
        self.logger = logging.getLogger("ml_predictor")

    def log_prediction(self, prediction: Dict[str, Any]):
        """Log prediction for monitoring and drift detection"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'entity_id': prediction['entity_id'],
            'predicted_location': prediction['predictions'][0]['location'],
            'confidence': prediction['predictions'][0]['confidence'],
            'method': prediction['method'],
            'latency_ms': prediction.get('latency_ms', 0)
        }

        self.logger.info(f"Prediction: {log_entry}")

        # Prometheus metrics
        prediction_counter.labels(
            entity_id=log_entry['entity_id'],
            model_version='v1',
            method=log_entry['method']
        ).inc()

    def log_feature_distribution(self, features: pd.DataFrame):
        """Log feature statistics for drift detection"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'feature_means': features.mean().to_dict(),
            'feature_stds': features.std().to_dict()
        }

        self.logger.debug(f"Feature stats: {stats}")
```

### 6.4 MLOps Improvements

#### Recommendation 1: Automated Retraining Pipeline
```python
# File: backend/services/ml/retraining_pipeline.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

class ModelRetrainingPipeline:
    def __init__(self, graph_builder, model_registry):
        self.graph = graph_builder
        self.registry = model_registry
        self.scheduler = BackgroundScheduler()

    def start_scheduler(self):
        """Start automated retraining schedule"""
        # Daily retraining at 2 AM
        self.scheduler.add_job(
            self.retrain_all_models,
            trigger='cron',
            hour=2,
            minute=0
        )
        self.scheduler.start()

    def retrain_all_models(self):
        """Retrain all entity models"""
        entities = self._get_entities_to_retrain()

        for entity_id in entities:
            try:
                self.retrain_entity_model(entity_id)
            except Exception as e:
                logging.error(f"Failed to retrain {entity_id}: {e}")

    def retrain_entity_model(self, entity_id: str):
        """Retrain model for specific entity"""
        # Fetch latest data
        events = self.graph.get_entity_timeline(entity_id)

        if len(events) < 10:
            return

        # Train new model
        predictor = LocationPredictor()
        result = predictor.train(events)

        if result['success']:
            # Evaluate on holdout set
            metrics = self._evaluate_model(predictor, events)

            # Register new version
            self.registry.register_model(
                predictor.model,
                entity_id,
                metrics
            )

            logging.info(f"Retrained model for {entity_id}: {metrics}")

    def _evaluate_model(self, predictor, events):
        """Evaluate model performance"""
        # Split data
        train_size = int(len(events) * 0.8)
        test_events = events[train_size:]

        # Predict on test set
        correct = 0
        total = 0

        for i, event in enumerate(test_events):
            if i == 0:
                continue

            prediction = predictor.predict(
                event['timestamp'],
                test_events[:i],
                top_k=1
            )

            if prediction['predictions']:
                predicted = prediction['predictions'][0]['location']
                actual = event['location']

                if predicted == actual:
                    correct += 1
                total += 1

        accuracy = correct / total if total > 0 else 0

        return {
            'accuracy': accuracy,
            'test_samples': total,
            'trained_at': datetime.now().isoformat()
        }
```

#### Recommendation 2: Model Drift Detection
```python
# File: backend/services/ml/drift_detection.py

from scipy.stats import ks_2samp
import pandas as pd

class DriftDetector:
    def __init__(self, reference_data: pd.DataFrame):
        self.reference_data = reference_data

    def detect_feature_drift(self, current_data: pd.DataFrame, threshold: float = 0.05):
        """Detect feature drift using Kolmogorov-Smirnov test"""
        drift_detected = {}

        for column in self.reference_data.columns:
            if column in current_data.columns:
                statistic, p_value = ks_2samp(
                    self.reference_data[column],
                    current_data[column]
                )

                drift_detected[column] = {
                    'statistic': statistic,
                    'p_value': p_value,
                    'drift': p_value < threshold
                }

        return drift_detected

    def detect_prediction_drift(self, predictions: List[Dict], window_size: int = 100):
        """Detect drift in prediction confidence"""
        recent_predictions = predictions[-window_size:]
        confidences = [p['predictions'][0]['confidence'] for p in recent_predictions]

        mean_confidence = np.mean(confidences)
        std_confidence = np.std(confidences)

        # Alert if average confidence drops below threshold
        if mean_confidence < 0.6:
            return {
                'alert': True,
                'mean_confidence': mean_confidence,
                'std_confidence': std_confidence,
                'message': 'Model confidence degraded, consider retraining'
            }

        return {'alert': False}
```

#### Recommendation 3: A/B Testing Framework
```python
# File: backend/services/ml/ab_testing.py

import random
from typing import Dict, List

class ABTestingFramework:
    def __init__(self):
        self.experiments = {}
        self.results = {}

    def create_experiment(self, experiment_id: str, variants: Dict[str, float]):
        """
        Create A/B test experiment

        Args:
            experiment_id: Unique experiment identifier
            variants: Dict of variant_name -> traffic_percentage
                     e.g., {'control': 0.5, 'treatment': 0.5}
        """
        assert sum(variants.values()) == 1.0, "Traffic must sum to 100%"

        self.experiments[experiment_id] = {
            'variants': variants,
            'created_at': datetime.now()
        }

        # Initialize results tracking
        self.results[experiment_id] = {
            variant: {'predictions': 0, 'correct': 0}
            for variant in variants.keys()
        }

    def select_variant(self, experiment_id: str, entity_id: str) -> str:
        """Select variant for entity (consistent hashing for same entity)"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return 'control'

        # Use hash of entity_id for deterministic assignment
        hash_value = hash(entity_id) % 100 / 100.0

        cumulative = 0
        for variant, percentage in experiment['variants'].items():
            cumulative += percentage
            if hash_value <= cumulative:
                return variant

        return list(experiment['variants'].keys())[0]

    def record_prediction(self, experiment_id: str, variant: str, correct: bool):
        """Record prediction outcome for variant"""
        if experiment_id in self.results:
            self.results[experiment_id][variant]['predictions'] += 1
            if correct:
                self.results[experiment_id][variant]['correct'] += 1

    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get experiment results with statistical significance"""
        results = self.results.get(experiment_id, {})

        summary = {}
        for variant, data in results.items():
            total = data['predictions']
            correct = data['correct']
            accuracy = correct / total if total > 0 else 0

            summary[variant] = {
                'predictions': total,
                'accuracy': accuracy,
                'correct': correct
            }

        # Calculate statistical significance (Chi-squared test)
        if len(summary) == 2:
            variants = list(summary.keys())
            v1, v2 = variants[0], variants[1]

            # Simplified significance test
            n1 = summary[v1]['predictions']
            n2 = summary[v2]['predictions']
            p1 = summary[v1]['accuracy']
            p2 = summary[v2]['accuracy']

            if n1 > 30 and n2 > 30:  # Sufficient sample size
                pooled_p = (summary[v1]['correct'] + summary[v2]['correct']) / (n1 + n2)
                se = np.sqrt(pooled_p * (1 - pooled_p) * (1/n1 + 1/n2))
                z_score = (p1 - p2) / se if se > 0 else 0

                summary['statistical_test'] = {
                    'z_score': z_score,
                    'significant': abs(z_score) > 1.96,  # 95% confidence
                    'better_variant': v1 if p1 > p2 else v2
                }

        return summary
```

---

## 7. Priority Implementation Roadmap

### Phase 1: Quick Wins (1-2 weeks)
1. **Model Caching** - Implement LRU cache for model loading
2. **Latency Instrumentation** - Add timing metrics to prediction pipeline
3. **Logging Infrastructure** - Structured logging for predictions
4. **Feature Engineering Refactor** - Separate feature extraction logic

**Expected Impact:** 50-70% latency reduction, better observability

### Phase 2: ML Infrastructure (2-4 weeks)
1. **MLflow Integration** - Model registry and versioning
2. **Evaluation Metrics** - Track accuracy, F1, precision, recall
3. **Batch Prediction API** - Support batch inference
4. **Model Compression** - Optimize model size (LightGBM migration)

**Expected Impact:** Better model management, 40% smaller models

### Phase 3: MLOps Foundation (4-6 weeks)
1. **Automated Retraining** - Scheduled daily retraining
2. **Drift Detection** - Monitor feature and prediction drift
3. **A/B Testing Framework** - Compare model versions
4. **Monitoring Dashboard** - Grafana + Prometheus integration

**Expected Impact:** Automated model lifecycle, early drift detection

### Phase 4: Advanced Optimization (6-8 weeks)
1. **Advanced Feature Engineering** - Location embeddings, interaction features
2. **Hyperparameter Tuning** - Automated tuning with Optuna
3. **Ensemble Models** - Combine multiple algorithms
4. **Real-time Monitoring** - Live model performance tracking

**Expected Impact:** 10-15% accuracy improvement, production-grade MLOps

---

## 8. Technology Stack Recommendations

### Current Stack
- **ML Framework:** scikit-learn (Random Forest)
- **Data Processing:** pandas, numpy
- **Model Storage:** pickle files
- **Database:** Neo4j (graph database)

### Recommended Additions

#### Model Registry & Experiment Tracking
```bash
pip install mlflow==2.10.0
```

#### Model Compression
```bash
pip install lightgbm==4.3.0  # Lighter alternative to Random Forest
pip install optuna==3.5.0    # Hyperparameter optimization
```

#### Monitoring & Drift Detection
```bash
pip install evidently==0.4.15         # Drift detection
pip install prometheus-client==0.19.0  # Metrics export
```

#### Inference Optimization
```bash
pip install redis==5.0.0   # Model cache
pip install joblib==1.3.2  # Efficient model loading
```

#### Testing & Validation
```bash
pip install pytest-benchmark==4.0.0  # Performance testing
pip install deepchecks==0.17.0       # ML validation
```

---

## 9. Security & Ethics Considerations

### Model Security
- ✅ Models stored locally (no external API calls for prediction)
- ⚠️ Pickle files vulnerable to code injection (use `joblib` or ONNX instead)
- ⚠️ No model authentication/authorization

**Recommendation:**
```python
# Use joblib for safer serialization
import joblib

# Save
joblib.dump(model, 'model.joblib', compress=3)

# Load
model = joblib.load('model.joblib')
```

### Privacy & Fairness
- ✅ No PII in features (entity_id is pseudonymized)
- ⚠️ No bias testing across demographic groups
- ⚠️ No fairness metrics implemented

**Recommendation:**
```python
# Example: Fairness testing
from aif360.datasets import BinaryLabelDataset
from aif360.metrics import ClassificationMetric

# Evaluate fairness across groups (e.g., student vs faculty)
metric = ClassificationMetric(
    dataset_true, dataset_pred,
    unprivileged_groups=[{'role': 'student'}],
    privileged_groups=[{'role': 'faculty'}]
)

print("Disparate Impact:", metric.disparate_impact())
print("Equal Opportunity Difference:", metric.equal_opportunity_difference())
```

---

## 10. Conclusion

The Fazri Analyzer has a solid foundation for ML-based location prediction with **31 trained Random Forest models** providing entity-specific predictions with explainability. However, significant gaps exist in MLOps infrastructure, model optimization, and production monitoring.

### Key Strengths
1. Explainable predictions with confidence scores
2. Well-structured code with clear separation
3. Lightweight models suitable for CPU inference
4. Comprehensive rule-based anomaly detection

### Critical Gaps
1. No model versioning or registry
2. No performance monitoring or drift detection
3. Synchronous model loading causing latency
4. No automated retraining or evaluation metrics
5. Limited feature engineering sophistication

### Recommended Next Steps
1. **Immediate (Week 1):** Implement model caching and latency instrumentation
2. **Short-term (Month 1):** Set up MLflow registry and automated retraining
3. **Medium-term (Quarter 1):** Build monitoring dashboard and drift detection
4. **Long-term (Quarter 2):** Advanced feature engineering and ensemble models

**Estimated ROI:**
- 50-70% latency reduction with caching
- 40% model size reduction with compression
- 10-15% accuracy improvement with better features
- 90% reduction in manual model management effort

---

**Analysis Completed:** 2026-03-15
**Next Review:** Recommended quarterly or after major system changes

