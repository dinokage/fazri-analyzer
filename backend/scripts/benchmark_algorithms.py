#!/usr/bin/env python3
"""
Comprehensive Performance Benchmark: Random Forest vs Alternative Algorithms
Location Prediction Task for Campus Security System

Benchmark Dimensions:
1. Inference Latency (P50, P95, P99)
2. Model Size (disk and memory)
3. Training Time
4. Memory Usage During Training/Inference
5. Throughput (predictions/second)
6. Accuracy Metrics (accuracy, precision, recall, F1)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
import pickle
import psutil
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import json

# ML Libraries
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

# Gradient Boosting Libraries
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("Warning: LightGBM not available. Install with: pip install lightgbm")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not available. Install with: pip install xgboost")

# Neural Network Libraries
try:
    from sklearn.neural_network import MLPClassifier
    NEURAL_NETWORK_AVAILABLE = True
except ImportError:
    NEURAL_NETWORK_AVAILABLE = False
    print("Warning: Neural Network not available")

from services.graph_builder import get_graph_builder


class PerformanceBenchmark:
    """Comprehensive performance benchmarking for location prediction algorithms"""

    def __init__(self):
        self.results = defaultdict(dict)
        self.graph = get_graph_builder()
        self.models_dir = Path(__file__).parent.parent / 'models'
        self.benchmark_dir = Path(__file__).parent.parent / 'benchmarks'
        self.benchmark_dir.mkdir(exist_ok=True)

    def get_memory_usage(self) -> float:
        """Get current process memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def get_model_size(self, model: Any) -> Dict[str, float]:
        """Get model size on disk and in memory"""
        # Save model temporarily to get disk size
        temp_path = self.benchmark_dir / 'temp_model.pkl'
        with open(temp_path, 'wb') as f:
            pickle.dump(model, f)

        disk_size_kb = temp_path.stat().st_size / 1024
        temp_path.unlink()

        # Estimate memory size (pickle serialization)
        memory_size_kb = len(pickle.dumps(model)) / 1024

        return {
            'disk_size_kb': disk_size_kb,
            'memory_size_kb': memory_size_kb,
            'disk_size_mb': disk_size_kb / 1024,
            'memory_size_mb': memory_size_kb / 1024
        }

    def prepare_training_data(self, entity_id: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Prepare features and labels for training"""
        # Get all events for this entity
        events = self.graph.get_entity_timeline(entity_id)

        if len(events) < 20:
            return None, None, None

        # Prepare training data
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Extract features
        features = []
        targets = []

        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            prev_row = df.iloc[i-1]

            # Time features
            hour = curr_row['timestamp'].hour
            day_of_week = curr_row['timestamp'].dayofweek

            # Previous location and event type
            prev_location = prev_row['location']
            prev_event_type = prev_row['event_type']

            # Time since last event (in hours)
            time_diff = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / 3600

            features.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'prev_location': prev_location,
                'prev_event_type': prev_event_type,
                'time_since_last': time_diff
            })

            targets.append(curr_row['location'])

        # Convert to DataFrame
        X_df = pd.DataFrame(features)
        y = targets

        # Encode categorical features
        location_encoder = LabelEncoder()
        event_encoder = LabelEncoder()

        location_encoder.fit(df['location'].unique())
        event_encoder.fit(df['event_type'].unique())

        X_df['prev_location_encoded'] = location_encoder.transform(X_df['prev_location'])
        X_df['prev_event_type_encoded'] = event_encoder.transform(X_df['prev_event_type'])

        # Select numeric features
        X = X_df[['hour', 'day_of_week', 'prev_location_encoded',
                  'prev_event_type_encoded', 'time_since_last']].values
        y_encoded = location_encoder.transform(y)

        metadata = {
            'total_samples': len(X),
            'unique_locations': len(location_encoder.classes_),
            'unique_event_types': len(event_encoder.classes_),
            'location_encoder': location_encoder,
            'event_encoder': event_encoder
        }

        return X, y_encoded, metadata

    def benchmark_training(self, X_train: np.ndarray, y_train: np.ndarray,
                          model_name: str, model: Any) -> Dict:
        """Benchmark training time and memory usage"""
        mem_before = self.get_memory_usage()

        start_time = time.perf_counter()
        model.fit(X_train, y_train)
        training_time = time.perf_counter() - start_time

        mem_after = self.get_memory_usage()
        mem_used = mem_after - mem_before

        return {
            'training_time_seconds': training_time,
            'memory_used_mb': mem_used,
            'memory_before_mb': mem_before,
            'memory_after_mb': mem_after
        }

    def benchmark_inference(self, model: Any, X_test: np.ndarray,
                           warmup_iterations: int = 100,
                           benchmark_iterations: int = 1000) -> Dict:
        """Benchmark inference latency and throughput"""
        # Warmup phase
        for _ in range(warmup_iterations):
            _ = model.predict(X_test[:10])

        # Benchmark single predictions
        latencies = []
        for i in range(benchmark_iterations):
            sample = X_test[i % len(X_test)].reshape(1, -1)
            start = time.perf_counter()
            _ = model.predict(sample)
            latency = (time.perf_counter() - start) * 1000  # Convert to ms
            latencies.append(latency)

        # Benchmark batch predictions
        batch_sizes = [1, 10, 100, 500]
        batch_throughput = {}

        for batch_size in batch_sizes:
            if batch_size > len(X_test):
                continue

            batch = X_test[:batch_size]
            start = time.perf_counter()
            iterations = min(100, 10000 // batch_size)
            for _ in range(iterations):
                _ = model.predict(batch)
            elapsed = time.perf_counter() - start
            throughput = (iterations * batch_size) / elapsed
            batch_throughput[f'batch_{batch_size}'] = throughput

        latencies = np.array(latencies)

        return {
            'latency_mean_ms': np.mean(latencies),
            'latency_median_ms': np.median(latencies),
            'latency_p95_ms': np.percentile(latencies, 95),
            'latency_p99_ms': np.percentile(latencies, 99),
            'latency_min_ms': np.min(latencies),
            'latency_max_ms': np.max(latencies),
            'latency_std_ms': np.std(latencies),
            'throughput_predictions_per_sec': 1000 / np.mean(latencies),
            'batch_throughput': batch_throughput
        }

    def benchmark_accuracy(self, model: Any, X_test: np.ndarray,
                          y_test: np.ndarray) -> Dict:
        """Benchmark prediction accuracy"""
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='weighted', zero_division=0
        )

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)

        # Top-K accuracy (if model has predict_proba)
        top_k_accuracy = {}
        if hasattr(model, 'predict_proba'):
            for k in [1, 3, 5]:
                y_proba = model.predict_proba(X_test)
                top_k_preds = np.argsort(y_proba, axis=1)[:, -k:]
                top_k_correct = np.array([y_test[i] in top_k_preds[i]
                                         for i in range(len(y_test))])
                top_k_accuracy[f'top_{k}_accuracy'] = np.mean(top_k_correct)

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix_shape': cm.shape,
            **top_k_accuracy
        }

    def create_models(self) -> Dict[str, Any]:
        """Create all models to benchmark"""
        models = {}

        # Random Forest (current baseline)
        models['RandomForest'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        # Logistic Regression (fast baseline)
        models['LogisticRegression'] = LogisticRegression(
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )

        # Gradient Boosting (sklearn)
        models['GradientBoosting'] = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )

        # LightGBM
        if LIGHTGBM_AVAILABLE:
            models['LightGBM'] = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )

        # XGBoost
        if XGBOOST_AVAILABLE:
            models['XGBoost'] = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
                verbosity=0
            )

        # Neural Network
        if NEURAL_NETWORK_AVAILABLE:
            models['NeuralNetwork'] = MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=200,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1
            )

        return models

    def benchmark_single_entity(self, entity_id: str, entity_name: str) -> Dict:
        """Benchmark all algorithms for a single entity"""
        print(f"\n{'='*70}")
        print(f"Benchmarking Entity: {entity_name} ({entity_id})")
        print(f"{'='*70}")

        # Prepare data
        X, y, metadata = self.prepare_training_data(entity_id)

        if X is None:
            print(f"Insufficient data for {entity_name}")
            return None

        print(f"\nDataset Statistics:")
        print(f"  Total samples: {metadata['total_samples']}")
        print(f"  Unique locations: {metadata['unique_locations']}")
        print(f"  Unique event types: {metadata['unique_event_types']}")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")

        # Create models
        models = self.create_models()
        entity_results = {}

        # Benchmark each model
        for model_name, model in models.items():
            print(f"\n{'-'*70}")
            print(f"Benchmarking: {model_name}")
            print(f"{'-'*70}")

            try:
                # Training benchmark
                print("  Training...", end=' ', flush=True)
                training_metrics = self.benchmark_training(X_train, y_train, model_name, model)
                print(f"✓ ({training_metrics['training_time_seconds']:.3f}s)")

                # Model size
                print("  Measuring size...", end=' ', flush=True)
                size_metrics = self.get_model_size(model)
                print(f"✓ ({size_metrics['disk_size_kb']:.1f}KB)")

                # Accuracy benchmark
                print("  Testing accuracy...", end=' ', flush=True)
                accuracy_metrics = self.benchmark_accuracy(model, X_test, y_test)
                print(f"✓ (Acc: {accuracy_metrics['accuracy']:.3f})")

                # Inference benchmark
                print("  Benchmarking inference...", end=' ', flush=True)
                inference_metrics = self.benchmark_inference(model, X_test)
                print(f"✓ (P95: {inference_metrics['latency_p95_ms']:.3f}ms)")

                # Store results
                entity_results[model_name] = {
                    **training_metrics,
                    **size_metrics,
                    **accuracy_metrics,
                    **inference_metrics,
                    'dataset_info': {
                        'train_samples': len(X_train),
                        'test_samples': len(X_test),
                        'unique_classes': metadata['unique_locations']
                    }
                }

            except Exception as e:
                print(f"✗ Failed: {str(e)}")
                entity_results[model_name] = {'error': str(e)}

        return entity_results

    def run_full_benchmark(self, max_entities: int = 5) -> Dict:
        """Run comprehensive benchmark across multiple entities"""
        print("\n" + "="*70)
        print("COMPREHENSIVE ALGORITHM PERFORMANCE BENCHMARK")
        print("Location Prediction Task - Campus Security System")
        print("="*70)

        # Get entities with sufficient data
        query = """
        MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
        WITH e, count(ev) as event_count
        WHERE event_count >= 50
        RETURN e.entity_id as entity_id, e.name as name, event_count
        ORDER BY event_count DESC
        LIMIT $limit
        """

        with self.graph.driver.session() as session:
            result = session.run(query, limit=max_entities)
            entities = [dict(record) for record in result]

        print(f"\nBenchmarking {len(entities)} entities with sufficient data")

        all_results = {}

        for entity in entities:
            entity_id = entity['entity_id']
            name = entity['name']

            results = self.benchmark_single_entity(entity_id, name)
            if results:
                all_results[entity_id] = {
                    'entity_name': name,
                    'event_count': entity['event_count'],
                    'benchmarks': results
                }

        # Generate aggregate statistics
        aggregate_stats = self.aggregate_results(all_results)

        return {
            'timestamp': datetime.now().isoformat(),
            'entities_benchmarked': len(all_results),
            'individual_results': all_results,
            'aggregate_statistics': aggregate_stats
        }

    def aggregate_results(self, all_results: Dict) -> Dict:
        """Aggregate results across all entities"""
        models = set()
        for entity_data in all_results.values():
            models.update(entity_data['benchmarks'].keys())

        aggregate = {}

        for model_name in models:
            metrics = defaultdict(list)

            for entity_data in all_results.values():
                if model_name in entity_data['benchmarks']:
                    model_results = entity_data['benchmarks'][model_name]

                    if 'error' not in model_results:
                        for key, value in model_results.items():
                            if isinstance(value, (int, float)):
                                metrics[key].append(value)

            # Calculate statistics
            aggregate[model_name] = {}
            for metric_name, values in metrics.items():
                if values:
                    aggregate[model_name][metric_name] = {
                        'mean': np.mean(values),
                        'median': np.median(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values)
                    }

        return aggregate

    def generate_comparison_table(self, results: Dict) -> str:
        """Generate formatted comparison table"""
        aggregate = results['aggregate_statistics']

        table = []
        table.append("\n" + "="*140)
        table.append("PERFORMANCE COMPARISON TABLE")
        table.append("="*140)

        # Header
        header = f"{'Algorithm':<20} {'Latency P95':<15} {'Throughput':<15} {'Accuracy':<12} {'Model Size':<15} {'Training Time':<15}"
        table.append(header)
        table.append("-"*140)

        # Rows
        for model_name in sorted(aggregate.keys()):
            stats = aggregate[model_name]

            latency_p95 = stats.get('latency_p95_ms', {}).get('mean', 0)
            throughput = stats.get('throughput_predictions_per_sec', {}).get('mean', 0)
            accuracy = stats.get('accuracy', {}).get('mean', 0)
            model_size = stats.get('disk_size_kb', {}).get('mean', 0)
            training_time = stats.get('training_time_seconds', {}).get('mean', 0)

            row = f"{model_name:<20} {latency_p95:>10.3f} ms   {throughput:>10.0f} p/s   {accuracy:>10.1%}  {model_size:>10.1f} KB   {training_time:>10.3f} s"
            table.append(row)

        table.append("="*140)

        return "\n".join(table)

    def generate_recommendation(self, results: Dict) -> str:
        """Generate data-driven recommendation"""
        aggregate = results['aggregate_statistics']

        # Score each algorithm
        scores = {}
        for model_name, stats in aggregate.items():
            score = 0

            # Accuracy (40% weight) - higher is better
            accuracy = stats.get('accuracy', {}).get('mean', 0)
            score += accuracy * 40

            # Latency (30% weight) - lower is better, normalize to 0-1
            latency = stats.get('latency_p95_ms', {}).get('mean', 100)
            latency_score = max(0, 1 - (latency / 10))  # Assume 10ms is bad
            score += latency_score * 30

            # Model size (20% weight) - lower is better
            size = stats.get('disk_size_kb', {}).get('mean', 1000)
            size_score = max(0, 1 - (size / 1000))  # Assume 1MB is bad
            score += size_score * 20

            # Training time (10% weight) - lower is better
            train_time = stats.get('training_time_seconds', {}).get('mean', 10)
            train_score = max(0, 1 - (train_time / 60))  # Assume 60s is bad
            score += train_score * 10

            scores[model_name] = score

        # Rank algorithms
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        recommendation = []
        recommendation.append("\n" + "="*70)
        recommendation.append("RECOMMENDATION FOR PRODUCTION DEPLOYMENT")
        recommendation.append("="*70)
        recommendation.append("\nAlgorithm Rankings (Higher score = Better overall performance):")
        recommendation.append("-"*70)

        for i, (model_name, score) in enumerate(ranked, 1):
            stats = aggregate[model_name]
            accuracy = stats.get('accuracy', {}).get('mean', 0)
            latency = stats.get('latency_p95_ms', {}).get('mean', 0)
            size = stats.get('disk_size_kb', {}).get('mean', 0)

            recommendation.append(f"\n{i}. {model_name} (Score: {score:.1f}/100)")
            recommendation.append(f"   Accuracy: {accuracy:.1%} | Latency P95: {latency:.3f}ms | Size: {size:.1f}KB")

        # Production recommendation
        recommendation.append("\n" + "="*70)
        recommendation.append("PRODUCTION RECOMMENDATION:")
        recommendation.append("="*70)

        winner = ranked[0][0]
        winner_stats = aggregate[winner]

        recommendation.append(f"\nBest Overall: {winner}")
        recommendation.append("\nRationale:")
        recommendation.append(f"- Accuracy: {winner_stats.get('accuracy', {}).get('mean', 0):.1%}")
        recommendation.append(f"- P95 Latency: {winner_stats.get('latency_p95_ms', {}).get('mean', 0):.3f}ms (Well within <10ms requirement)")
        recommendation.append(f"- Model Size: {winner_stats.get('disk_size_kb', {}).get('mean', 0):.1f}KB × 31 models = {winner_stats.get('disk_size_kb', {}).get('mean', 0) * 31 / 1024:.1f}MB total")
        recommendation.append(f"- Training Time: {winner_stats.get('training_time_seconds', {}).get('mean', 0):.2f}s per model")
        recommendation.append(f"- Throughput: {winner_stats.get('throughput_predictions_per_sec', {}).get('mean', 0):.0f} predictions/sec")

        # Alternative recommendation
        if len(ranked) > 1:
            alternative = ranked[1][0]
            alt_stats = aggregate[alternative]
            recommendation.append(f"\nAlternative Option: {alternative}")
            recommendation.append(f"- Slightly different trade-offs: Accuracy {alt_stats.get('accuracy', {}).get('mean', 0):.1%}, "
                                f"Latency {alt_stats.get('latency_p95_ms', {}).get('mean', 0):.3f}ms")

        recommendation.append("\n" + "="*70)

        return "\n".join(recommendation)

    def save_results(self, results: Dict):
        """Save benchmark results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON results
        json_path = self.benchmark_dir / f'benchmark_results_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Save comparison table
        table_path = self.benchmark_dir / f'benchmark_comparison_{timestamp}.txt'
        with open(table_path, 'w') as f:
            f.write(self.generate_comparison_table(results))
            f.write("\n\n")
            f.write(self.generate_recommendation(results))

        print(f"\n\nResults saved to:")
        print(f"  JSON: {json_path}")
        print(f"  Report: {table_path}")

        return json_path, table_path

    def cleanup(self):
        """Cleanup resources"""
        self.graph.close()


def main():
    """Run comprehensive benchmark"""
    benchmark = PerformanceBenchmark()

    try:
        # Run benchmark on 5 entities with most data
        results = benchmark.run_full_benchmark(max_entities=5)

        # Print comparison table
        print(benchmark.generate_comparison_table(results))

        # Print recommendation
        print(benchmark.generate_recommendation(results))

        # Save results
        benchmark.save_results(results)

    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()
