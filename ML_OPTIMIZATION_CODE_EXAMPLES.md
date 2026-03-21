# ML Performance Optimization - Implementation Guide

This document provides ready-to-use code examples for implementing the performance optimizations identified in the benchmark analysis.

---

## 1. Multiprocessing Deployment (8-10x Improvement)

### Option A: Gunicorn Configuration (Recommended)

**File:** `gunicorn.conf.py`

```python
"""
Gunicorn configuration for production deployment
Expected throughput: 2,000-2,400 req/sec (8-10x improvement)
"""

import multiprocessing

# Worker configuration
workers = multiprocessing.cpu_count() - 1  # Leave 1 core for OS
worker_class = 'sync'  # Use sync workers (not async) for CPU-bound ML tasks
threads = 1  # Don't use threads - GIL bottleneck!

# Performance tuning
max_requests = 1000  # Restart workers after 1000 requests (prevent memory leaks)
max_requests_jitter = 100  # Add randomness to avoid thundering herd
timeout = 30  # 30 second timeout for long-running predictions
keepalive = 5  # Keep connections alive for 5 seconds

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048  # Pending connection queue size

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'fazri-ml-api'

# Pre-load application code before forking workers
preload_app = True  # Share model loading across workers

def on_starting(server):
    """Called just before the master process is initialized"""
    print(f"Starting Gunicorn with {workers} workers")

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT signal"""
    print(f"Worker {worker.pid} received INT signal")

def post_fork(server, worker):
    """Called after a worker has been forked"""
    print(f"Worker spawned (pid: {worker.pid})")
```

**Deployment:**
```bash
# Install Gunicorn
pip install gunicorn

# Run with configuration file
gunicorn -c gunicorn.conf.py app:app

# Or use command-line arguments
gunicorn -w 8 --worker-class sync --timeout 30 --max-requests 1000 app:app
```

### Option B: Custom Multiprocessing Pool

**File:** `services/multiprocess_predictor.py`

```python
"""
Custom multiprocessing pool for ML predictions
Use this if you can't deploy with Gunicorn
"""

from multiprocessing import Pool, Manager
import pickle
from pathlib import Path
from typing import Dict, List
import os

# Global model cache (per worker process)
_model_cache = {}

def load_model_worker(entity_id: str):
    """Load model in worker process (avoids GIL)"""
    global _model_cache

    if entity_id not in _model_cache:
        model_path = Path("models") / f"predictor_{entity_id}.pkl"
        with open(model_path, 'rb') as f:
            _model_cache[entity_id] = pickle.load(f)

    return _model_cache[entity_id]

def predict_worker(args):
    """Worker function for parallel prediction"""
    entity_id, target_time, recent_events = args

    # Load model (cached after first call)
    model_data = load_model_worker(entity_id)

    # Create predictor instance
    from services.ml_predictor import LocationPredictor
    predictor = LocationPredictor()
    predictor.model = model_data['model']
    predictor.location_encoder = model_data['location_encoder']
    predictor.event_encoder = model_data['event_encoder']
    predictor.feature_importance = model_data['feature_importance']
    predictor.is_trained = True

    # Make prediction
    return predictor.predict(target_time, recent_events, top_k=3)

class MultiprocessPredictor:
    """Thread-safe multiprocess prediction service"""

    def __init__(self, num_workers=None):
        if num_workers is None:
            num_workers = os.cpu_count() - 1

        self.pool = Pool(processes=num_workers)
        print(f"Initialized multiprocess predictor with {num_workers} workers")

    def predict_batch(self, requests: List[tuple]) -> List[Dict]:
        """
        Predict in parallel using multiprocessing

        Args:
            requests: List of (entity_id, target_time, recent_events) tuples

        Returns:
            List of prediction results
        """
        # Submit all requests to pool
        results = self.pool.map(predict_worker, requests)
        return results

    def predict_single(self, entity_id: str, target_time, recent_events: List[Dict]) -> Dict:
        """Single prediction (uses pool for consistency)"""
        results = self.pool.map(predict_worker, [(entity_id, target_time, recent_events)])
        return results[0]

    def close(self):
        """Shutdown the pool"""
        self.pool.close()
        self.pool.join()

# Singleton instance
_predictor = None

def get_multiprocess_predictor():
    """Get or create multiprocess predictor"""
    global _predictor
    if _predictor is None:
        _predictor = MultiprocessPredictor()
    return _predictor
```

**Usage in FastAPI:**
```python
from fastapi import FastAPI
from services.multiprocess_predictor import get_multiprocess_predictor

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Initialize multiprocess pool on startup
    get_multiprocess_predictor()

@app.post("/predict")
async def predict(request: PredictionRequest):
    predictor = get_multiprocess_predictor()
    result = predictor.predict_single(
        request.entity_id,
        request.target_time,
        request.recent_events
    )
    return result
```

---

## 2. Redis Caching Layer (50-100x for Cache Hits)

### Installation

```bash
# Install Redis client
pip install redis

# Start Redis server (Docker)
docker run -d -p 6379:6379 redis:latest

# Or install locally
brew install redis  # macOS
redis-server  # Start server
```

### Implementation

**File:** `services/prediction_cache.py`

```python
"""
Redis-based prediction caching
Expected cache hit rate: 60-80%
Expected speedup on cache hits: 50-100x
"""

import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PredictionCache:
    """Redis-backed prediction cache with intelligent key generation"""

    def __init__(self,
                 redis_url: str = "redis://localhost:6379/0",
                 ttl_seconds: int = 3600):
        """
        Args:
            redis_url: Redis connection URL
            ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _generate_cache_key(self,
                           entity_id: str,
                           target_time: datetime,
                           granularity: str = 'hour') -> str:
        """
        Generate cache key for prediction

        Granularity options:
        - 'hour': Cache predictions for same hour (recommended)
        - 'day': Cache predictions for same day
        - 'exact': Cache exact timestamp (low hit rate)
        """
        if granularity == 'hour':
            time_key = target_time.strftime('%Y%m%d%H')
        elif granularity == 'day':
            time_key = target_time.strftime('%Y%m%d')
        else:  # exact
            time_key = target_time.isoformat()

        return f"pred:v1:{entity_id}:{time_key}"

    def get(self,
            entity_id: str,
            target_time: datetime,
            granularity: str = 'hour') -> Optional[Dict]:
        """
        Get cached prediction

        Returns:
            Cached prediction dict or None if not found
        """
        cache_key = self._generate_cache_key(entity_id, target_time, granularity)

        try:
            cached_data = self.client.get(cache_key)

            if cached_data:
                self.hits += 1
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(cached_data)
            else:
                self.misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.misses += 1
            return None

    def set(self,
            entity_id: str,
            target_time: datetime,
            prediction: Dict,
            granularity: str = 'hour',
            ttl: Optional[int] = None):
        """
        Cache prediction

        Args:
            entity_id: Entity ID
            target_time: Target prediction time
            prediction: Prediction result to cache
            granularity: Time granularity for cache key
            ttl: Optional TTL override (default: self.ttl)
        """
        cache_key = self._generate_cache_key(entity_id, target_time, granularity)
        ttl = ttl or self.ttl

        try:
            # Serialize prediction to JSON
            cached_data = json.dumps(prediction, default=str)

            # Set with TTL
            self.client.setex(cache_key, ttl, cached_data)
            logger.debug(f"Cached prediction: {cache_key} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.get_hit_rate(),
            'redis_info': self.client.info('stats')
        }

    def invalidate_entity(self, entity_id: str):
        """Invalidate all cached predictions for an entity"""
        pattern = f"pred:v1:{entity_id}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries for {entity_id}")

    def clear_all(self):
        """Clear all cached predictions"""
        pattern = "pred:v1:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries")

# Singleton instance
_cache = None

def get_cache() -> PredictionCache:
    """Get or create cache instance"""
    global _cache
    if _cache is None:
        _cache = PredictionCache()
    return _cache
```

### Integration with ML Predictor

**File:** `services/ml_predictor.py` (add caching wrapper)

```python
from services.prediction_cache import get_cache

def predict_with_cache(
    predictor: LocationPredictor,
    entity_id: str,
    target_time: datetime,
    recent_events: List[Dict],
    top_k: int = 3
) -> Dict:
    """
    Predict with caching layer

    Cache hit: ~0.01-0.05ms (70x faster)
    Cache miss: ~0.70ms (normal prediction)
    """
    cache = get_cache()

    # Try cache first
    cached_result = cache.get(entity_id, target_time, granularity='hour')
    if cached_result:
        cached_result['cache_hit'] = True
        return cached_result

    # Cache miss - compute prediction
    result = predictor.predict(target_time, recent_events, top_k)
    result['cache_hit'] = False

    # Cache for future requests
    cache.set(entity_id, target_time, result, granularity='hour', ttl=3600)

    return result
```

### FastAPI Integration with Monitoring

```python
from fastapi import FastAPI, Depends
from services.prediction_cache import get_cache

app = FastAPI()

@app.get("/cache/stats")
async def get_cache_stats():
    """Endpoint to monitor cache performance"""
    cache = get_cache()
    return cache.get_stats()

@app.post("/predict")
async def predict(request: PredictionRequest):
    """Predict with caching"""
    result = predict_with_cache(
        predictor,
        request.entity_id,
        request.target_time,
        request.recent_events
    )

    return {
        "prediction": result,
        "cache_hit": result.get('cache_hit', False),
        "latency_ms": 0.05 if result['cache_hit'] else 0.70  # Approximate
    }
```

---

## 3. Vectorized Batch Processing (3-5x Improvement)

### Current Implementation (Inefficient)

```python
# Current: Sequential processing in loop
def predict_batch_sequential(self, batch_requests: List[tuple]) -> List[Dict]:
    """Inefficient: Processes one at a time"""
    results = []
    for entity_id, target_time, recent_events in batch_requests:
        result = self.predict(target_time, recent_events)
        results.append(result)
    return results

# Time for 100 items: 100 × 0.70ms = 70ms
```

### Optimized Implementation (Vectorized)

**File:** `services/ml_predictor.py` (add batch methods)

```python
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

class LocationPredictor:
    # ... existing code ...

    def extract_features_batch(self,
                               batch_data: List[Tuple[datetime, List[Dict]]]) -> np.ndarray:
        """
        Vectorized feature extraction for batch predictions
        3-5x faster than sequential processing
        """
        features_list = []

        for target_time, recent_events in batch_data:
            if not recent_events:
                continue

            # Get most recent event
            df = pd.DataFrame(recent_events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            last_event = df.iloc[-1]

            # Extract features (same as single prediction)
            hour = target_time.hour
            day_of_week = target_time.weekday()
            prev_location = last_event['location']
            prev_event_type = last_event['event_type']
            time_since_last = (target_time - last_event['timestamp']).total_seconds() / 3600

            features_list.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'prev_location': prev_location,
                'prev_event_type': prev_event_type,
                'time_since_last': time_since_last
            })

        if not features_list:
            return np.array([])

        # Convert to DataFrame for vectorized encoding
        features_df = pd.DataFrame(features_list)

        # Vectorized encoding (1000x faster than loop)
        try:
            features_df['prev_location_encoded'] = self.location_encoder.transform(
                features_df['prev_location']
            )
            features_df['prev_event_encoded'] = self.event_encoder.transform(
                features_df['prev_event_type']
            )
        except ValueError:
            # Handle unknown categories
            return np.array([])

        # Return as numpy array
        X = features_df[['hour', 'day_of_week', 'prev_location_encoded',
                        'prev_event_encoded', 'time_since_last']].values

        return X

    def predict_batch(self,
                     batch_data: List[Tuple[datetime, List[Dict]]],
                     top_k: int = 3) -> List[Dict]:
        """
        Vectorized batch prediction - 3-5x faster than sequential

        Args:
            batch_data: List of (target_time, recent_events) tuples
            top_k: Number of top predictions to return

        Returns:
            List of prediction dictionaries
        """
        if not self.is_trained:
            return [self._fallback_predict(t, e) for t, e in batch_data]

        # Extract features for all items at once (vectorized)
        X_batch = self.extract_features_batch(batch_data)

        if len(X_batch) == 0:
            return [{'predictions': [], 'method': 'no_data'} for _ in batch_data]

        # Single vectorized prediction call (much faster than loop)
        probabilities_batch = self.model.predict_proba(X_batch)

        # Process results
        results = []
        for i, (target_time, recent_events) in enumerate(batch_data):
            probabilities = probabilities_batch[i]

            # Get top K predictions
            top_indices = np.argsort(probabilities)[-top_k:][::-1]

            predictions = []
            for idx in top_indices:
                location = self.location_encoder.inverse_transform([idx])[0]
                confidence = probabilities[idx]

                # Generate explanation (can also be batched)
                explanation = self._generate_explanation(
                    location, confidence,
                    X_batch[i, 0],  # hour
                    X_batch[i, 1],  # day_of_week
                    recent_events[-1]['location'] if recent_events else None,
                    recent_events
                )

                predictions.append({
                    'location': location,
                    'confidence': round(float(confidence), 3),
                    'explanation': explanation
                })

            results.append({
                'target_time': target_time.isoformat(),
                'predictions': predictions,
                'method': 'random_forest_ml_batch'
            })

        return results

# Time for 100 items: ~15-20ms (3-5x faster!)
```

### FastAPI Batch Endpoint

```python
from pydantic import BaseModel
from typing import List
from datetime import datetime

class BatchPredictionRequest(BaseModel):
    requests: List[Dict]  # List of {entity_id, target_time, recent_events}

@app.post("/predict/batch")
async def predict_batch(request: BatchPredictionRequest):
    """
    Batch prediction endpoint
    3-5x faster than multiple single predictions
    """
    # Extract data for batch processing
    batch_data = [
        (
            datetime.fromisoformat(req['target_time']),
            req['recent_events']
        )
        for req in request.requests
    ]

    # Vectorized batch prediction
    results = predictor.predict_batch(batch_data, top_k=3)

    return {
        'predictions': results,
        'batch_size': len(results),
        'method': 'vectorized_batch'
    }
```

---

## 4. ONNX Runtime Conversion (30-50x Improvement)

### Installation

```bash
pip install skl2onnx onnxruntime
```

### Model Conversion Script

**File:** `scripts/convert_to_onnx.py`

```python
"""
Convert scikit-learn RandomForest models to ONNX format
Expected speedup: 3-5x per prediction
Enables: GPU acceleration, true multi-threading (no GIL)
"""

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import pickle
import onnx
import onnxruntime as rt
import numpy as np
from pathlib import Path

def convert_model_to_onnx(model_path: Path, output_path: Path):
    """
    Convert scikit-learn model to ONNX format

    Args:
        model_path: Path to pickle file
        output_path: Path to save ONNX model
    """
    # Load sklearn model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']

    # Define input type (5 features, batch size can vary)
    initial_type = [('float_input', FloatTensorType([None, 5]))]

    # Convert to ONNX
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        target_opset=12  # ONNX opset version
    )

    # Save ONNX model
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    print(f"Converted {model_path.name} to ONNX")

    # Verify conversion
    session = rt.InferenceSession(str(output_path))
    print(f"  Input name: {session.get_inputs()[0].name}")
    print(f"  Input shape: {session.get_inputs()[0].shape}")
    print(f"  Output name: {session.get_outputs()[0].name}")

def convert_all_models():
    """Convert all models to ONNX"""
    models_dir = Path("models")
    onnx_dir = Path("models_onnx")
    onnx_dir.mkdir(exist_ok=True)

    for model_file in models_dir.glob("predictor_*.pkl"):
        onnx_file = onnx_dir / model_file.with_suffix('.onnx').name
        convert_model_to_onnx(model_file, onnx_file)

if __name__ == "__main__":
    convert_all_models()
```

### ONNX Runtime Predictor

**File:** `services/onnx_predictor.py`

```python
"""
ONNX Runtime-based predictor
30-50x faster throughput, no GIL limitations
"""

import onnxruntime as rt
import numpy as np
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import pickle

class ONNXLocationPredictor:
    """ONNX Runtime predictor with vectorized inference"""

    def __init__(self, model_path: Path):
        # Load ONNX model
        self.session = rt.InferenceSession(str(model_path))
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # Load encoders from original pickle
        pickle_path = model_path.with_suffix('.pkl')
        with open(pickle_path, 'rb') as f:
            model_data = pickle.load(f)
            self.location_encoder = model_data['location_encoder']
            self.event_encoder = model_data['event_encoder']
            self.feature_importance = model_data['feature_importance']

    def extract_features(self, target_time: datetime, recent_events: List[Dict]) -> np.ndarray:
        """Extract features (same as sklearn version)"""
        if not recent_events:
            return None

        # Get most recent event
        last_event = max(recent_events, key=lambda x: x['timestamp'])

        hour = target_time.hour
        day_of_week = target_time.weekday()
        prev_location = last_event['location']
        prev_event_type = last_event['event_type']

        # Encode
        try:
            prev_location_encoded = self.location_encoder.transform([prev_location])[0]
            prev_event_encoded = self.event_encoder.transform([prev_event_type])[0]
        except ValueError:
            return None

        time_diff = (target_time - last_event['timestamp']).total_seconds() / 3600

        features = np.array([[
            hour,
            day_of_week,
            prev_location_encoded,
            prev_event_encoded,
            time_diff
        ]], dtype=np.float32)

        return features

    def predict(self, target_time: datetime, recent_events: List[Dict], top_k: int = 3) -> Dict:
        """
        Predict using ONNX Runtime (3-5x faster than sklearn)
        """
        features = self.extract_features(target_time, recent_events)

        if features is None:
            return {'predictions': [], 'method': 'no_data'}

        # ONNX inference (C++ backend, no GIL!)
        probabilities = self.session.run(
            [self.output_name],
            {self.input_name: features}
        )[0][0]

        # Get top K predictions
        top_indices = np.argsort(probabilities)[-top_k:][::-1]

        predictions = []
        for idx in top_indices:
            location = self.location_encoder.inverse_transform([idx])[0]
            confidence = probabilities[idx]

            predictions.append({
                'location': location,
                'confidence': round(float(confidence), 3)
            })

        return {
            'target_time': target_time.isoformat(),
            'predictions': predictions,
            'method': 'onnx_runtime'
        }

    def predict_batch(self, batch_data: List[tuple]) -> List[Dict]:
        """
        Batch prediction with ONNX Runtime
        Supports true multi-threading (no GIL!)
        """
        # Extract all features
        features_list = []
        valid_indices = []

        for i, (target_time, recent_events) in enumerate(batch_data):
            features = self.extract_features(target_time, recent_events)
            if features is not None:
                features_list.append(features[0])
                valid_indices.append(i)

        if not features_list:
            return [{'predictions': [], 'method': 'no_data'}] * len(batch_data)

        # Batch inference (single C++ call)
        batch_features = np.vstack(features_list).astype(np.float32)
        probabilities_batch = self.session.run(
            [self.output_name],
            {self.input_name: batch_features}
        )[0]

        # Format results
        results = []
        for i, (target_time, _) in enumerate(batch_data):
            if i not in valid_indices:
                results.append({'predictions': [], 'method': 'no_data'})
                continue

            prob_idx = valid_indices.index(i)
            probabilities = probabilities_batch[prob_idx]

            top_indices = np.argsort(probabilities)[-3:][::-1]

            predictions = [{
                'location': self.location_encoder.inverse_transform([idx])[0],
                'confidence': round(float(probabilities[idx]), 3)
            } for idx in top_indices]

            results.append({
                'target_time': target_time.isoformat(),
                'predictions': predictions,
                'method': 'onnx_batch'
            })

        return results
```

### Performance Comparison

```python
# Benchmark ONNX vs scikit-learn
import time

# Load both models
sklearn_predictor = LocationPredictor()
sklearn_predictor.load_model("models/predictor_E100001.pkl")

onnx_predictor = ONNXLocationPredictor(Path("models_onnx/predictor_E100001.onnx"))

# Test data
test_events = generate_test_events(100)
target_time = datetime.now()

# Benchmark sklearn
start = time.time()
for _ in range(1000):
    sklearn_predictor.predict(target_time, test_events)
sklearn_time = time.time() - start

# Benchmark ONNX
start = time.time()
for _ in range(1000):
    onnx_predictor.predict(target_time, test_events)
onnx_time = time.time() - start

print(f"scikit-learn: {sklearn_time:.3f}s (1,000 predictions)")
print(f"ONNX Runtime: {onnx_time:.3f}s (1,000 predictions)")
print(f"Speedup: {sklearn_time / onnx_time:.2f}x")

# Expected output:
# scikit-learn: 0.700s (1,000 predictions)
# ONNX Runtime: 0.200s (1,000 predictions)
# Speedup: 3.5x
```

---

## 5. Monitoring & Performance Metrics

### Custom Prometheus Metrics

**File:** `monitoring/metrics.py`

```python
"""
Prometheus metrics for ML performance monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

# Prediction latency histogram (milliseconds)
prediction_latency = Histogram(
    'ml_prediction_latency_ms',
    'Prediction latency in milliseconds',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000]
)

# Prediction throughput counter
prediction_total = Counter(
    'ml_predictions_total',
    'Total number of predictions',
    ['model_id', 'method']  # Labels
)

# Cache hit rate
cache_hits = Counter('ml_cache_hits_total', 'Cache hits')
cache_misses = Counter('ml_cache_misses_total', 'Cache misses')

# Model load time
model_load_time = Histogram(
    'ml_model_load_seconds',
    'Model load time in seconds',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

# Active predictions gauge
active_predictions = Gauge(
    'ml_active_predictions',
    'Number of predictions currently being processed'
)

# Model info
model_info = Info('ml_model', 'ML model information')

def track_prediction_latency(func):
    """Decorator to track prediction latency"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        active_predictions.inc()

        try:
            result = func(*args, **kwargs)
            latency_ms = (time.time() - start) * 1000
            prediction_latency.observe(latency_ms)

            # Track method
            method = result.get('method', 'unknown')
            prediction_total.labels(model_id='default', method=method).inc()

            # Track cache hits
            if result.get('cache_hit'):
                cache_hits.inc()
            else:
                cache_misses.inc()

            return result

        finally:
            active_predictions.dec()

    return wrapper

# Example usage
@track_prediction_latency
def predict_with_monitoring(predictor, target_time, recent_events):
    return predictor.predict(target_time, recent_events)
```

### Grafana Dashboard JSON

**File:** `monitoring/grafana-dashboard.json`

```json
{
  "dashboard": {
    "title": "ML Performance Dashboard",
    "panels": [
      {
        "title": "Prediction Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ml_prediction_latency_ms_bucket)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Predictions per Second",
        "targets": [
          {
            "expr": "rate(ml_predictions_total[1m])"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "ml_cache_hits_total / (ml_cache_hits_total + ml_cache_misses_total)"
          }
        ],
        "type": "singlestat"
      }
    ]
  }
}
```

---

## Complete Example: Optimized FastAPI Application

**File:** `app_optimized.py`

```python
"""
Optimized FastAPI application with all performance improvements
Expected throughput: 2,000-12,000 req/sec depending on configuration
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Import optimized components
from services.prediction_cache import get_cache
from services.onnx_predictor import ONNXLocationPredictor
from monitoring.metrics import track_prediction_latency, prediction_total

app = FastAPI(title="Fazri Analyzer ML API - Optimized")

# Global model cache
models = {}

@app.on_event("startup")
async def startup():
    """Initialize models on startup"""
    logger = logging.getLogger(__name__)
    logger.info("Loading ONNX models...")

    # Load ONNX models (lazy loading)
    # Actual loading happens on first request

    logger.info("Startup complete")

def get_model(entity_id: str) -> ONNXLocationPredictor:
    """Lazy load models on demand"""
    if entity_id not in models:
        model_path = Path(f"models_onnx/predictor_{entity_id}.onnx")
        if not model_path.exists():
            raise HTTPException(status_code=404, message=f"Model not found for {entity_id}")

        models[entity_id] = ONNXLocationPredictor(model_path)

    return models[entity_id]

class PredictionRequest(BaseModel):
    entity_id: str
    target_time: datetime
    recent_events: List[Dict]
    use_cache: bool = True

@app.post("/predict")
@track_prediction_latency
async def predict(request: PredictionRequest):
    """
    Optimized prediction endpoint with caching
    Expected latency: 0.01-0.30ms
    """
    cache = get_cache()

    # Check cache first
    if request.use_cache:
        cached = cache.get(request.entity_id, request.target_time)
        if cached:
            cached['cache_hit'] = True
            return cached

    # Load model and predict
    model = get_model(request.entity_id)
    result = model.predict(request.target_time, request.recent_events)
    result['cache_hit'] = False

    # Cache result
    if request.use_cache:
        cache.set(request.entity_id, request.target_time, result)

    return result

@app.post("/predict/batch")
@track_prediction_latency
async def predict_batch(requests: List[PredictionRequest]):
    """
    Vectorized batch prediction
    Expected throughput: 5,000-8,000 predictions/sec
    """
    # Group by entity_id for batch processing
    by_entity = {}
    for req in requests:
        if req.entity_id not in by_entity:
            by_entity[req.entity_id] = []
        by_entity[req.entity_id].append((req.target_time, req.recent_events))

    # Process each entity's batch
    all_results = []
    for entity_id, batch_data in by_entity.items():
        model = get_model(entity_id)
        results = model.predict_batch(batch_data)
        all_results.extend(results)

    return {'predictions': all_results, 'count': len(all_results)}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
async def health():
    """Health check endpoint"""
    cache = get_cache()
    return {
        'status': 'healthy',
        'models_loaded': len(models),
        'cache_hit_rate': cache.get_hit_rate()
    }
```

### Deployment Configuration

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  ml-api:
    build: .
    command: gunicorn -c gunicorn.conf.py app_optimized:app
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 4G

  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Summary of Expected Improvements

| Optimization | Implementation Time | Expected Impact | Complexity |
|-------------|-------------------|-----------------|------------|
| Gunicorn multiprocessing | 1 day | **8-10x throughput** | Low |
| Redis caching | 2-3 days | **50-100x for cache hits** | Low |
| Batch vectorization | 1-2 days | **3-5x batch throughput** | Medium |
| ONNX conversion | 2-3 weeks | **30-50x throughput** | High |
| Combined (All) | 1 month | **100-200x overall** | Medium |

**Recommended Implementation Order:**
1. Gunicorn multiprocessing (Day 1)
2. Redis caching (Week 1)
3. Batch vectorization (Week 2)
4. ONNX conversion (Month 2-3, optional)
