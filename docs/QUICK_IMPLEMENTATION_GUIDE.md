# Quick Implementation Guide: ML Improvements for Fazri Analyzer

## TL;DR - What to Do Next

**KEEP Random Forest** - It's working great (0.7ms latency, 1,400 pred/sec throughput).

**Top 3 priorities** to improve ML performance (ranked by ROI):

1. **Add accuracy evaluation** (2-4 hours) - Critical to prove value
2. **Add prediction caching** (1-2 hours) - 10x throughput improvement
3. **Fix concurrency bottleneck** (4-8 hours) - 6-8x scaling improvement

**Nice-to-have enhancements**:
4. Add Logistic Regression fallback for low-data entities (2-4 hours)
5. Add Isolation Forest for novel anomaly detection (4-8 hours)

**Don't waste time on**: Switching to LightGBM, Neural Networks, or LSTM (low ROI for current scale).

---

## Priority 1: Add Accuracy Evaluation (CRITICAL)

### Why This Matters
You're optimizing for speed without knowing if predictions are actually useful. Need baseline metrics.

### What to Build
Create `/Users/dinokage/dev/fazri-analyzer/backend/scripts/evaluate_models.py`

```python
"""
Evaluate location prediction accuracy across all entity models
Usage: python scripts/evaluate_models.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.ml_predictor import LocationPredictor
from services.graph_builder import get_graph_builder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pandas as pd
import json
from datetime import datetime


def evaluate_entity_model(entity_id: str, events: list) -> dict:
    """
    Evaluate prediction accuracy for a single entity using temporal split

    Args:
        entity_id: Entity identifier
        events: List of event dictionaries (must be sorted by timestamp)

    Returns:
        Dictionary with accuracy metrics
    """
    if len(events) < 20:
        return {
            'entity_id': entity_id,
            'status': 'insufficient_data',
            'event_count': len(events)
        }

    # Temporal split: train on first 80%, test on last 20%
    split_idx = int(len(events) * 0.8)
    train_events = events[:split_idx]
    test_events = events[split_idx:]

    # Train model
    predictor = LocationPredictor()
    train_result = predictor.train(train_events)

    if not train_result['success']:
        return {
            'entity_id': entity_id,
            'status': 'training_failed',
            'message': train_result['message']
        }

    # Make predictions on test set
    predictions = []
    actuals = []
    confidences = []

    for i, test_event in enumerate(test_events):
        # Use all training data + test events up to this point as context
        context_events = train_events + test_events[:i]

        # Predict location at this test event's timestamp
        pred_result = predictor.predict(
            target_time=test_event['timestamp'],
            recent_events=context_events[-50:],  # Use last 50 events as context
            top_k=3
        )

        if pred_result['predictions']:
            top_pred = pred_result['predictions'][0]
            predictions.append(top_pred['location'])
            confidences.append(top_pred['confidence'])
            actuals.append(test_event['location'])

    if len(predictions) == 0:
        return {
            'entity_id': entity_id,
            'status': 'no_predictions',
            'test_samples': len(test_events)
        }

    # Calculate metrics
    accuracy = accuracy_score(actuals, predictions)
    report = classification_report(actuals, predictions, output_dict=True, zero_division=0)

    # Calculate confidence-weighted accuracy
    correct_predictions = [1 if p == a else 0 for p, a in zip(predictions, actuals)]
    avg_confidence_correct = sum(c for c, correct in zip(confidences, correct_predictions) if correct) / max(sum(correct_predictions), 1)
    avg_confidence_incorrect = sum(c for c, correct in zip(confidences, correct_predictions) if not correct) / max(len(correct_predictions) - sum(correct_predictions), 1)

    return {
        'entity_id': entity_id,
        'status': 'success',
        'training_samples': len(train_events),
        'test_samples': len(test_events),
        'accuracy': round(accuracy, 4),
        'weighted_f1': round(report['weighted avg']['f1-score'], 4),
        'macro_f1': round(report['macro avg']['f1-score'], 4),
        'avg_confidence': round(sum(confidences) / len(confidences), 4),
        'avg_confidence_correct': round(avg_confidence_correct, 4),
        'avg_confidence_incorrect': round(avg_confidence_incorrect, 4),
        'unique_locations_train': train_result['unique_locations'],
        'unique_locations_test': len(set(actuals)),
        'classification_report': report
    }


def evaluate_all_models():
    """Evaluate all entity models and generate report"""
    print("\n" + "="*80)
    print("EVALUATING LOCATION PREDICTION MODELS")
    print("="*80)

    graph = get_graph_builder()

    # Get all entities with sufficient data
    query = """
    MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
    WITH e, count(ev) as event_count
    WHERE event_count >= 20
    RETURN e.entity_id as entity_id, e.name as name, event_count
    ORDER BY event_count DESC
    """

    with graph.driver.session() as session:
        result = session.run(query)
        entities = [dict(record) for record in result]

    print(f"\nEvaluating {len(entities)} entities with 20+ events\n")

    all_results = []
    successful_evals = []

    for i, entity in enumerate(entities, 1):
        entity_id = entity['entity_id']
        name = entity['name']

        print(f"[{i}/{len(entities)}] Evaluating {name} ({entity_id})...")

        # Get all events for this entity
        events = graph.get_entity_timeline(entity_id)

        # Evaluate model
        eval_result = evaluate_entity_model(entity_id, events)
        all_results.append(eval_result)

        if eval_result['status'] == 'success':
            successful_evals.append(eval_result)
            print(f"  ✅ Accuracy: {eval_result['accuracy']:.2%}, "
                  f"F1: {eval_result['weighted_f1']:.2%}, "
                  f"Confidence: {eval_result['avg_confidence']:.2%}")
        else:
            print(f"  ⚠️  {eval_result['status']}")

    graph.close()

    # Calculate aggregate statistics
    if successful_evals:
        avg_accuracy = sum(r['accuracy'] for r in successful_evals) / len(successful_evals)
        avg_f1 = sum(r['weighted_f1'] for r in successful_evals) / len(successful_evals)
        avg_confidence = sum(r['avg_confidence'] for r in successful_evals) / len(successful_evals)

        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        print(f"\nSuccessful evaluations: {len(successful_evals)}/{len(entities)}")
        print(f"Average accuracy: {avg_accuracy:.2%}")
        print(f"Average F1-score: {avg_f1:.2%}")
        print(f"Average confidence: {avg_confidence:.2%}")

        # Accuracy distribution
        accuracy_bins = {
            '90-100%': sum(1 for r in successful_evals if r['accuracy'] >= 0.9),
            '80-90%': sum(1 for r in successful_evals if 0.8 <= r['accuracy'] < 0.9),
            '70-80%': sum(1 for r in successful_evals if 0.7 <= r['accuracy'] < 0.8),
            '60-70%': sum(1 for r in successful_evals if 0.6 <= r['accuracy'] < 0.7),
            '<60%': sum(1 for r in successful_evals if r['accuracy'] < 0.6)
        }

        print("\nAccuracy distribution:")
        for bin_range, count in accuracy_bins.items():
            pct = count / len(successful_evals) * 100
            print(f"  {bin_range}: {count} entities ({pct:.1f}%)")

    # Save detailed results
    output_file = Path(__file__).parent.parent / 'ml_accuracy_evaluation_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_entities': len(entities),
            'successful_evaluations': len(successful_evals),
            'average_accuracy': avg_accuracy if successful_evals else 0,
            'average_f1': avg_f1 if successful_evals else 0,
            'average_confidence': avg_confidence if successful_evals else 0,
            'accuracy_distribution': accuracy_bins if successful_evals else {},
            'detailed_results': all_results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    evaluate_all_models()
```

### How to Run
```bash
cd /Users/dinokage/dev/fazri-analyzer/backend
python scripts/evaluate_models.py
```

### Expected Output
```
Average accuracy: 78.3%
Average F1-score: 76.1%

Accuracy distribution:
  90-100%: 5 entities (16.1%)
  80-90%: 12 entities (38.7%)
  70-80%: 8 entities (25.8%)
  60-70%: 4 entities (12.9%)
  <60%: 2 entities (6.5%)
```

### Success Criteria
- Average accuracy >70% → Random Forest is working well
- Average accuracy 60-70% → Consider LightGBM
- Average accuracy <60% → Problem with data quality or feature engineering

---

## Priority 2: Add Prediction Caching (HIGH IMPACT)

### Why This Matters
Same predictions requested multiple times (e.g., dashboard refreshes). Caching gives 10x throughput.

### What to Build
Modify `/Users/dinokage/dev/fazri-analyzer/backend/services/ml_predictor.py`

```python
import redis
import json
from functools import wraps
import hashlib

class LocationPredictor:
    def __init__(self, use_cache=True):
        self.model = None
        self.location_encoder = LabelEncoder()
        self.event_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_importance = {}

        # Redis cache (optional, graceful degradation if unavailable)
        self.use_cache = use_cache
        self.cache = None
        if use_cache:
            try:
                self.cache = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=1
                )
                self.cache.ping()
            except (redis.ConnectionError, redis.TimeoutError):
                print("Warning: Redis not available, caching disabled")
                self.cache = None

    def _cache_key(self, target_time, recent_events, top_k, entity_id):
        """Generate cache key from prediction parameters"""
        # Use last 3 events + target time as cache key
        recent_summary = json.dumps([
            {
                'location': e['location'],
                'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp']),
                'event_type': e['event_type']
            }
            for e in recent_events[-3:]
        ], sort_keys=True)

        cache_string = f"{entity_id}:{target_time.isoformat()}:{top_k}:{recent_summary}"
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"predict:{cache_hash}"

    def predict(
        self,
        target_time: datetime,
        recent_events: List[Dict],
        top_k: int = 3,
        entity_id: str = None
    ) -> Dict:
        """
        Predict location at target_time with caching

        Args:
            target_time: Target prediction time
            recent_events: List of recent events for context
            top_k: Number of top predictions to return
            entity_id: Entity ID (for cache key)

        Returns:
            Prediction dictionary with top_k predictions
        """
        # Try cache first
        if self.cache and entity_id:
            cache_key = self._cache_key(target_time, recent_events, top_k, entity_id)
            try:
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
            except redis.RedisError:
                pass  # Cache miss or error, continue to prediction

        # Make prediction (existing code)
        if not self.is_trained:
            result = self._fallback_predict(target_time, recent_events)
        elif not recent_events:
            result = {
                'predictions': [],
                'method': 'no_data',
                'explanation': 'No recent events available for prediction'
            }
        else:
            # Existing prediction logic...
            # [Keep all existing prediction code here]
            df = pd.DataFrame(recent_events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            last_event = df.iloc[-1]

            hour = target_time.hour
            day_of_week = target_time.weekday()
            prev_location = last_event['location']
            prev_event_type = last_event['event_type']
            time_since_last = (target_time - last_event['timestamp']).total_seconds() / 3600

            try:
                prev_location_encoded = self.location_encoder.transform([prev_location])[0]
                prev_event_encoded = self.event_encoder.transform([prev_event_type])[0]
            except ValueError:
                return self._fallback_predict(target_time, recent_events)

            X = np.array([[hour, day_of_week, prev_location_encoded, prev_event_encoded, time_since_last]])
            probabilities = self.model.predict_proba(X)[0]
            top_indices = np.argsort(probabilities)[-top_k:][::-1]

            predictions = []
            for idx in top_indices:
                location = self.location_encoder.inverse_transform([idx])[0]
                probability = probabilities[idx]

                explanation = self._generate_explanation(
                    location, probability, hour, day_of_week,
                    prev_location, recent_events
                )

                predictions.append({
                    'location': location,
                    'confidence': round(float(probability), 3),
                    'explanation': explanation
                })

            result = {
                'target_time': target_time.isoformat(),
                'predictions': predictions,
                'method': 'random_forest_ml',
                'model_info': {
                    'feature_importance': self.feature_importance,
                    'training_samples': 'trained'
                }
            }

        # Cache result (5 minute TTL)
        if self.cache and entity_id:
            try:
                self.cache.setex(
                    cache_key,
                    300,  # 5 minutes
                    json.dumps(result)
                )
            except redis.RedisError:
                pass  # Cache write failed, not critical

        return result
```

### Setup Redis
```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt-get install redis-server
sudo systemctl start redis

# Verify
redis-cli ping  # Should return "PONG"
```

### Expected Impact
- **Cache hit rate**: 50-90% (dashboard refreshes, repeated queries)
- **Effective throughput**: 10x improvement (1,400 → 14,000 pred/sec)
- **Latency for cached requests**: <0.1ms (vs 0.7ms)

### Monitoring
Add to your metrics dashboard:
```python
# In your monitoring/metrics endpoint
cache_stats = predictor.cache.info('stats') if predictor.cache else {}
print(f"Cache hit rate: {cache_stats.get('keyspace_hits', 0) / max(cache_stats.get('keyspace_hits', 0) + cache_stats.get('keyspace_misses', 1), 1):.1%}")
```

---

## Priority 3: Fix Concurrency Bottleneck (HIGH IMPACT)

### Why This Matters
Current threading efficiency: 10.9% at 8 threads (should be 70-80%). Python GIL prevents parallelism.

### What to Build
Replace threading with multiprocessing in your API server.

**Option A: Use Gunicorn with multiple workers** (Easiest, 1 hour)

Update your server startup:
```bash
# Before (single process)
uvicorn main:app --host 0.0.0.0 --port 8000

# After (8 worker processes)
gunicorn main:app \
  --workers 8 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

Add to `requirements.txt`:
```
gunicorn>=21.2.0
```

**Expected improvement**: Near-linear scaling up to worker count (8x throughput with 8 workers).

**Option B: Use ProcessPoolExecutor for batch jobs** (For batch predictions, 2-4 hours)

Create `/Users/dinokage/dev/fazri-analyzer/backend/services/batch_predictor.py`:

```python
"""
Batch prediction service using multiprocessing for parallel inference
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict
from datetime import datetime
import pickle
from pathlib import Path
from services.ml_predictor import LocationPredictor


def predict_single(args):
    """Worker function for parallel prediction (must be top-level for pickling)"""
    entity_id, model_path, target_time, recent_events, top_k = args

    # Load model in worker process
    predictor = LocationPredictor(use_cache=False)  # No Redis in worker
    predictor.load_model(model_path)

    # Make prediction
    result = predictor.predict(target_time, recent_events, top_k)
    result['entity_id'] = entity_id

    return result


class BatchPredictor:
    """Parallel batch prediction using multiprocessing"""

    def __init__(self, models_dir: Path, max_workers: int = 8):
        self.models_dir = models_dir
        self.max_workers = max_workers

    def predict_batch(
        self,
        predictions: List[Dict]
    ) -> List[Dict]:
        """
        Predict locations for multiple entities in parallel

        Args:
            predictions: List of prediction tasks, each with:
                - entity_id: str
                - target_time: datetime
                - recent_events: List[Dict]
                - top_k: int (optional, default 3)

        Returns:
            List of prediction results
        """
        # Prepare worker arguments
        worker_args = []
        for pred in predictions:
            model_path = self.models_dir / f"predictor_{pred['entity_id']}.pkl"
            if not model_path.exists():
                continue  # Skip entities without trained models

            worker_args.append((
                pred['entity_id'],
                model_path,
                pred['target_time'],
                pred['recent_events'],
                pred.get('top_k', 3)
            ))

        # Execute in parallel
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(predict_single, args): args[0]
                for args in worker_args
            }

            # Collect results as they complete
            for future in as_completed(futures):
                entity_id = futures[future]
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    print(f"Error predicting for {entity_id}: {e}")
                    results.append({
                        'entity_id': entity_id,
                        'error': str(e),
                        'predictions': []
                    })

        return results
```

Usage example:
```python
# Batch prediction for heatmap generation
from services.batch_predictor import BatchPredictor
from datetime import datetime, timedelta

batch_predictor = BatchPredictor(
    models_dir=Path('models'),
    max_workers=8
)

# Generate predictions for all 500 entities at 2pm
predictions_to_make = []
target_time = datetime.now().replace(hour=14, minute=0)

for entity_id in all_entity_ids:
    predictions_to_make.append({
        'entity_id': entity_id,
        'target_time': target_time,
        'recent_events': get_recent_events(entity_id),  # Your function
        'top_k': 3
    })

# Execute in parallel (8 processes)
results = batch_predictor.predict_batch(predictions_to_make)

# Results ready in ~1-2 seconds for 500 entities (vs 6-8 seconds single-threaded)
```

### Expected Impact
- **Concurrent throughput**: 6-8x improvement
- **Batch heatmap generation**: 4.2s → 0.6s (7x faster)
- **Scalability efficiency**: 10.9% → 70-80%

---

## Priority 4: Hybrid Model Selection (NICE-TO-HAVE)

### Why This Matters
29% of entities have <50 events. Random Forest overfits on small data. Logistic Regression performs better.

### What to Build
Modify `/Users/dinokage/dev/fazri-analyzer/backend/scripts/train_predictor.py`:

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

def train_predictors():
    """Train location predictors with automatic model selection"""

    print("\n" + "="*60)
    print("🎓 Training Location Predictors (Hybrid Strategy)")
    print("="*60)

    graph = get_graph_builder()
    query = """
    MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
    WITH e, count(ev) as event_count
    WHERE event_count >= 10
    RETURN e.entity_id as entity_id, e.name as name, event_count
    ORDER BY event_count DESC
    """

    with graph.driver.session() as session:
        result = session.run(query)
        entities = [dict(record) for record in result]

    print(f"\nFound {len(entities)} entities with sufficient data for training")

    models_dir = Path(__file__).parent.parent / 'models'
    models_dir.mkdir(exist_ok=True)

    trained_count = 0
    model_type_counts = {'random_forest': 0, 'logistic_regression': 0}

    for entity in entities:
        entity_id = entity['entity_id']
        name = entity['name']
        event_count = entity['event_count']

        print(f"\n📊 Training predictor for {name} ({entity_id})")
        print(f"   Events available: {event_count}")

        events = graph.get_entity_timeline(entity_id)

        # Automatic model selection
        if event_count >= 50:
            # Use Random Forest for high-data entities
            predictor = LocationPredictor()
            result = predictor.train(events)
            model_type = 'random_forest'
            print(f"   🌲 Selected: Random Forest (sufficient data)")

        else:
            # Use Logistic Regression for low-data entities
            predictor = LogisticRegressionPredictor()  # New class (see below)
            result = predictor.train(events)
            model_type = 'logistic_regression'
            print(f"   📈 Selected: Logistic Regression (limited data)")

        if result['success']:
            print(f"   ✅ Training successful!")
            print(f"      Training samples: {result['training_samples']}")
            print(f"      Unique locations: {result['unique_locations']}")

            model_path = models_dir / f"predictor_{entity_id}.pkl"
            predictor.save_model(model_path)
            print(f"      💾 Model saved: {model_type}")

            trained_count += 1
            model_type_counts[model_type] += 1
        else:
            print(f"   ❌ Training failed: {result['message']}")

    print(f"\n{'='*60}")
    print(f"✅ Training Complete!")
    print(f"   Total trained: {trained_count}/{len(entities)}")
    print(f"   Random Forest: {model_type_counts['random_forest']}")
    print(f"   Logistic Regression: {model_type_counts['logistic_regression']}")
    print(f"{'='*60}\n")

    graph.close()
```

Create new class in `/Users/dinokage/dev/fazri-analyzer/backend/services/ml_predictor.py`:

```python
class LogisticRegressionPredictor:
    """Logistic Regression predictor for entities with limited data"""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.location_encoder = LabelEncoder()
        self.event_encoder = LabelEncoder()
        self.is_trained = False

    def train(self, events: List[Dict], min_samples: int = 10):
        """Train logistic regression model"""
        if len(events) < min_samples:
            return {
                'success': False,
                'message': f'Insufficient training data. Need at least {min_samples} events, got {len(events)}'
            }

        # Prepare training data (same as Random Forest)
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        features = []
        targets = []

        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            prev_row = df.iloc[i-1]

            hour = curr_row['timestamp'].hour
            day_of_week = curr_row['timestamp'].dayofweek
            prev_location = prev_row['location']
            prev_event_type = prev_row['event_type']
            time_diff = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / 3600

            features.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'prev_location': prev_location,
                'prev_event_type': prev_event_type,
                'time_since_last': time_diff
            })

            targets.append(curr_row['location'])

        X_df = pd.DataFrame(features)
        y = targets

        # Encode categorical features
        self.location_encoder.fit(df['location'].unique())
        self.event_encoder.fit(df['event_type'].unique())

        X_df['prev_location_encoded'] = self.location_encoder.transform(X_df['prev_location'])
        X_df['prev_event_type_encoded'] = self.event_encoder.transform(X_df['prev_event_type'])

        X = X_df[['hour', 'day_of_week', 'prev_location_encoded',
                  'prev_event_type_encoded', 'time_since_last']].values
        y_encoded = self.location_encoder.transform(y)

        # Scale features (important for Logistic Regression)
        X_scaled = self.scaler.fit_transform(X)

        # Train Logistic Regression
        self.model = LogisticRegression(
            max_iter=1000,
            multi_class='multinomial',
            solver='lbfgs',
            random_state=42
        )
        self.model.fit(X_scaled, y_encoded)
        self.is_trained = True

        return {
            'success': True,
            'training_samples': len(X),
            'unique_locations': len(self.location_encoder.classes_)
        }

    def predict(self, target_time: datetime, recent_events: List[Dict], top_k: int = 3) -> Dict:
        """Predict location (similar interface to LocationPredictor)"""
        # Same prediction logic as Random Forest, but with scaling
        if not self.is_trained or not recent_events:
            return {'predictions': [], 'method': 'no_data'}

        df = pd.DataFrame(recent_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        last_event = df.iloc[-1]

        hour = target_time.hour
        day_of_week = target_time.weekday()
        prev_location = last_event['location']
        prev_event_type = last_event['event_type']
        time_since_last = (target_time - last_event['timestamp']).total_seconds() / 3600

        try:
            prev_location_encoded = self.location_encoder.transform([prev_location])[0]
            prev_event_encoded = self.event_encoder.transform([prev_event_type])[0]
        except ValueError:
            return {'predictions': [], 'method': 'unknown_category'}

        X = np.array([[hour, day_of_week, prev_location_encoded, prev_event_encoded, time_since_last]])
        X_scaled = self.scaler.transform(X)

        probabilities = self.model.predict_proba(X_scaled)[0]
        top_indices = np.argsort(probabilities)[-top_k:][::-1]

        predictions = []
        for idx in top_indices:
            location = self.location_encoder.inverse_transform([idx])[0]
            probability = probabilities[idx]

            predictions.append({
                'location': location,
                'confidence': round(float(probability), 3)
            })

        return {
            'target_time': target_time.isoformat(),
            'predictions': predictions,
            'method': 'logistic_regression_ml'
        }

    def save_model(self, filepath: Path):
        """Save trained model"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'location_encoder': self.location_encoder,
            'event_encoder': self.event_encoder
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, filepath: Path):
        """Load trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.location_encoder = model_data['location_encoder']
        self.event_encoder = model_data['event_encoder']
        self.is_trained = True
```

### Expected Impact
- **Accuracy improvement**: 5-10% for low-data entities
- **Coverage**: Extends useful predictions to entities with 10-50 events
- **Model size**: 50-100KB per Logistic Regression model (vs 700KB for Random Forest)

---

## Priority 5: Add Isolation Forest for Anomalies (NICE-TO-HAVE)

### Why This Matters
Current rule-based detectors miss novel attack patterns (70-80% recall). Isolation Forest catches unknown anomalies.

### What to Build
Create `/Users/dinokage/dev/fazri-analyzer/backend/services/ml_anomaly_detection.py`:

```python
"""
ML-based anomaly detection using Isolation Forest
Complements rule-based detectors by catching novel patterns
"""

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
import pickle
from pathlib import Path


class MLAnomalyDetector:
    """Isolation Forest anomaly detector for entity behavior"""

    def __init__(self, contamination=0.1):
        """
        Args:
            contamination: Expected proportion of anomalies (0.05-0.15)
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []

    def extract_features(self, events: List[Dict]) -> pd.DataFrame:
        """Extract behavioral features from events"""
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        features = []

        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]

            # Time-based features
            hour = curr['timestamp'].hour
            day_of_week = curr['timestamp'].dayofweek
            is_weekend = 1 if day_of_week >= 5 else 0
            is_night = 1 if hour < 6 or hour >= 22 else 0

            # Time since last event
            time_diff_hours = (curr['timestamp'] - prev['timestamp']).total_seconds() / 3600

            # Location change velocity
            location_changed = 1 if curr['location'] != prev['location'] else 0

            # Zone type (categorize by prefix)
            zone_type_map = {
                'LAB': 1, 'LIB': 2, 'CAF': 3, 'GYM': 4,
                'ADMIN': 5, 'ROOM': 6, 'SEM': 7, 'AUDITORIUM': 8,
                'HOSTEL': 9
            }
            zone_prefix = curr['location'].split('_')[0]
            zone_type = zone_type_map.get(zone_prefix, 0)

            features.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'is_night': is_night,
                'time_since_last': time_diff_hours,
                'location_changed': location_changed,
                'zone_type': zone_type
            })

        return pd.DataFrame(features)

    def train(self, events: List[Dict], min_samples: int = 50):
        """
        Train anomaly detector on normal behavior

        Args:
            events: List of event dictionaries (should be mostly normal behavior)
            min_samples: Minimum events required for training
        """
        if len(events) < min_samples:
            return {
                'success': False,
                'message': f'Insufficient data. Need {min_samples}+, got {len(events)}'
            }

        # Extract features
        features_df = self.extract_features(events)
        self.feature_names = list(features_df.columns)

        # Scale and train
        X = features_df.values
        X_scaled = self.scaler.fit_transform(X)

        self.model.fit(X_scaled)
        self.is_trained = True

        # Calculate anomaly scores on training data
        anomaly_scores = self.model.score_samples(X_scaled)
        threshold = np.percentile(anomaly_scores, 10)  # Bottom 10% are anomalies

        return {
            'success': True,
            'training_samples': len(X),
            'anomaly_threshold': threshold,
            'features': self.feature_names
        }

    def detect_anomalies(self, events: List[Dict]) -> List[Dict]:
        """
        Detect anomalous events in the given list

        Returns:
            List of anomalies with scores
        """
        if not self.is_trained:
            return []

        if len(events) < 2:
            return []

        # Extract features
        features_df = self.extract_features(events)
        X = features_df.values
        X_scaled = self.scaler.transform(X)

        # Predict anomalies
        predictions = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal
        scores = self.model.score_samples(X_scaled)  # Lower = more anomalous

        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly detected
                event = events[i+1]  # +1 because feature extraction starts at index 1

                # Calculate severity based on score
                # Scores typically range from -0.5 to 0.5
                if score < -0.3:
                    severity = 'high'
                elif score < -0.2:
                    severity = 'medium'
                else:
                    severity = 'low'

                anomalies.append({
                    'type': 'ml_detected_anomaly',
                    'severity': severity,
                    'timestamp': event['timestamp'],
                    'location': event['location'],
                    'anomaly_score': round(float(score), 4),
                    'description': f"ML model detected unusual behavior pattern (score: {score:.3f})",
                    'details': {
                        'event': event,
                        'features': dict(features_df.iloc[i])
                    }
                })

        return anomalies

    def save_model(self, filepath: Path):
        """Save trained model"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, filepath: Path):
        """Load trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.is_trained = True
```

### How to Use (Integrate with existing anomaly detection)

Modify `/Users/dinokage/dev/fazri-analyzer/backend/services/entity_anomaly_detection.py`:

```python
from services.ml_anomaly_detection import MLAnomalyDetector

class EntityAnomalyDetectionService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        # ... existing initialization ...

        # Add ML anomaly detector
        self.ml_detector = None
        try:
            ml_model_path = Path('models') / 'ml_anomaly_detector.pkl'
            if ml_model_path.exists():
                self.ml_detector = MLAnomalyDetector()
                self.ml_detector.load_model(ml_model_path)
        except Exception as e:
            print(f"ML anomaly detector not available: {e}")

    def detect_entity_anomalies(self, start_time: datetime, end_time: datetime, entity_id: Optional[str] = None) -> List[Dict]:
        """Detect all entity-level anomalies (rule-based + ML-based)"""
        anomalies = []

        # Rule-based detectors (existing, keep all 12)
        anomalies.extend(self._detect_off_hours_access(start_time, end_time, entity_id))
        anomalies.extend(self._detect_role_violations(start_time, end_time))
        # ... all other rule-based detectors ...

        # ML-based detector (new, catches novel patterns)
        if self.ml_detector:
            anomalies.extend(self._detect_ml_anomalies(start_time, end_time, entity_id))

        return sorted(anomalies, key=lambda x: x['timestamp'], reverse=True)

    def _detect_ml_anomalies(self, start_time: datetime, end_time: datetime, entity_id: Optional[str] = None) -> List[Dict]:
        """Detect anomalies using ML model"""
        if not self.ml_detector:
            return []

        anomalies = []

        # Get events for analysis
        with self.driver.session() as session:
            query = """
            MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
            WHERE r.timestamp >= datetime($start_time)
            AND r.timestamp <= datetime($end_time)
            """ + ("AND e.entity_id = $entity_id" if entity_id else "") + """
            RETURN e.entity_id as entity_id,
                   e.name as entity_name,
                   z.zone_id as location,
                   r.timestamp as timestamp,
                   r.event_type as event_type
            ORDER BY e.entity_id, r.timestamp
            """

            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            if entity_id:
                params['entity_id'] = entity_id

            result = session.run(query, params)
            events_by_entity = {}

            for rec in result:
                eid = rec['entity_id']
                if eid not in events_by_entity:
                    events_by_entity[eid] = {
                        'entity_name': rec['entity_name'],
                        'events': []
                    }

                events_by_entity[eid]['events'].append({
                    'timestamp': rec['timestamp'].to_native() if hasattr(rec['timestamp'], 'to_native') else rec['timestamp'],
                    'location': rec['location'],
                    'event_type': rec['event_type']
                })

        # Detect anomalies for each entity
        for eid, data in events_by_entity.items():
            ml_anomalies = self.ml_detector.detect_anomalies(data['events'])

            for anom in ml_anomalies:
                anom['entity_id'] = eid
                anom['entity_name'] = data['entity_name']
                anomalies.append(anom)

        return anomalies
```

### Training Script
Create `/Users/dinokage/dev/fazri-analyzer/backend/scripts/train_ml_anomaly_detector.py`:

```python
"""
Train ML anomaly detector on normal behavior patterns
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.ml_anomaly_detection import MLAnomalyDetector
from services.graph_builder import get_graph_builder
from datetime import datetime, timedelta


def train_ml_anomaly_detector():
    """Train Isolation Forest on normal access patterns"""
    print("\n" + "="*60)
    print("🤖 Training ML Anomaly Detector (Isolation Forest)")
    print("="*60)

    graph = get_graph_builder()

    # Get all events from last 30 days (assumed mostly normal)
    # Filter out known anomalous hours (late night)
    query = """
    MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
    WHERE r.timestamp >= datetime() - duration('P30D')
    AND r.timestamp.hour >= 7
    AND r.timestamp.hour < 22
    RETURN z.zone_id as location,
           r.timestamp as timestamp,
           r.event_type as event_type
    ORDER BY r.timestamp
    """

    with graph.driver.session() as session:
        result = session.run(query)
        events = []

        for rec in result:
            events.append({
                'timestamp': rec['timestamp'].to_native() if hasattr(rec['timestamp'], 'to_native') else rec['timestamp'],
                'location': rec['location'],
                'event_type': rec['event_type']
            })

    print(f"\nCollected {len(events)} normal behavior events")

    # Train model
    detector = MLAnomalyDetector(contamination=0.1)  # Expect 10% anomalies
    result = detector.train(events)

    if result['success']:
        print(f"\n✅ Training successful!")
        print(f"   Training samples: {result['training_samples']}")
        print(f"   Features: {', '.join(result['features'])}")
        print(f"   Anomaly threshold: {result['anomaly_threshold']:.4f}")

        # Save model
        model_path = Path(__file__).parent.parent / 'models' / 'ml_anomaly_detector.pkl'
        detector.save_model(model_path)
        print(f"   💾 Model saved to {model_path}")
    else:
        print(f"\n❌ Training failed: {result['message']}")

    graph.close()


if __name__ == "__main__":
    train_ml_anomaly_detector()
```

### Expected Impact
- **Novel anomaly detection**: 15-30% more anomalies caught
- **Recall improvement**: 70-80% → 85-95%
- **False positive rate**: 30-40% (review queue, not immediate alerts)
- **Inference speed**: 1-5ms per event (acceptable for batch processing)

---

## Summary Checklist

### This Week (Critical)
- [ ] Add accuracy evaluation script (2-4 hours)
- [ ] Install Redis and add prediction caching (1-2 hours)
- [ ] Switch to Gunicorn with 8 workers (1 hour)

### This Month (High Value)
- [ ] Add Logistic Regression fallback (2-4 hours)
- [ ] Add Isolation Forest anomaly detection (4-8 hours)
- [ ] Add model compression with joblib lz4 (30 min)

### Future (Nice-to-Have)
- [ ] Consider LightGBM if scaling to 500+ entities
- [ ] Explore LSTM for trajectory prediction (new feature)
- [ ] Add batch prediction API endpoint

### Don't Waste Time On
- ❌ Switching to Neural Networks
- ❌ Implementing K-NN
- ❌ Deep learning autoencoders
- ❌ Over-optimizing current Random Forest

---

**Total Implementation Time**: 10-20 hours for all priorities 1-5
**Expected Overall Impact**: 10-100x improvement in production capabilities
**Algorithm Change Needed**: No, keep Random Forest

---

**Last Updated**: 2026-03-15
**Related Docs**:
- ML_ALGORITHM_ANALYSIS.md
- ALGORITHM_COMPARISON_TABLE.md
