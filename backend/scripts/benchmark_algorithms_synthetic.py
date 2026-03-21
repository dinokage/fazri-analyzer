#!/usr/bin/env python3
"""
Comprehensive Performance Benchmark: Random Forest vs Alternative Algorithms
Location Prediction Task - Using Synthetic Representative Data

This benchmark creates synthetic data that mimics the characteristics of real campus
security data to compare different ML algorithms without requiring database access.
"""

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
from pathlib import Path

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

# Neural Network
from sklearn.neural_network import MLPClassifier


class SyntheticDataGenerator:
    """Generate synthetic campus security data for benchmarking"""

    def __init__(self, seed=42):
        np.random.seed(seed)
        self.locations = [
            'MAIN_GATE', 'LIBRARY', 'CAFETERIA', 'LAB_A', 'LAB_B',
            'CLASSROOM_101', 'CLASSROOM_201', 'ADMIN_BUILDING', 'PARKING_LOT',
            'SPORTS_COMPLEX', 'AUDITORIUM', 'HOSTEL_A', 'HOSTEL_B'
        ]
        self.event_types = ['entry', 'exit']

    def generate_entity_patterns(self, n_samples=1000) -> pd.DataFrame:
        """
        Generate realistic entity movement patterns
        Simulates a student/staff member's daily routine with:
        - Time-based location patterns (morning at hostel, afternoon at classes)
        - Sequential movement patterns (realistic transitions)
        - Some randomness/variation
        """
        events = []
        start_date = datetime.now() - timedelta(days=90)

        # Define typical daily patterns
        daily_pattern = {
            range(0, 7): 'HOSTEL_A',  # Midnight to 7am - at hostel
            range(7, 9): ['HOSTEL_A', 'CAFETERIA', 'MAIN_GATE'],  # Morning routine
            range(9, 12): ['CLASSROOM_101', 'CLASSROOM_201', 'LAB_A', 'LAB_B'],  # Morning classes
            range(12, 13): 'CAFETERIA',  # Lunch
            range(13, 17): ['CLASSROOM_101', 'CLASSROOM_201', 'LAB_A', 'LIBRARY'],  # Afternoon
            range(17, 19): ['CAFETERIA', 'SPORTS_COMPLEX', 'LIBRARY'],  # Evening
            range(19, 24): ['HOSTEL_A', 'CAFETERIA']  # Night
        }

        current_time = start_date
        current_location = 'HOSTEL_A'

        for i in range(n_samples):
            # Add some time variation (1-4 hours)
            current_time += timedelta(hours=np.random.uniform(1, 4))

            hour = current_time.hour

            # Determine next location based on time of day
            for time_range, locations in daily_pattern.items():
                if hour in time_range:
                    if isinstance(locations, list):
                        # 70% chance of following pattern, 30% random
                        if np.random.random() < 0.7:
                            next_location = np.random.choice(locations)
                        else:
                            next_location = np.random.choice(self.locations)
                    else:
                        next_location = locations
                    break

            # Don't repeat same location consecutively too often
            if next_location == current_location and np.random.random() < 0.8:
                next_location = np.random.choice([l for l in self.locations if l != current_location])

            event_type = np.random.choice(self.event_types)

            events.append({
                'timestamp': current_time,
                'location': next_location,
                'event_type': event_type,
                'hour': current_time.hour,
                'day_of_week': current_time.weekday()
            })

            current_location = next_location

        return pd.DataFrame(events)

    def prepare_ml_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Convert event data to ML features"""
        # Encode categorical features
        location_encoder = LabelEncoder()
        event_encoder = LabelEncoder()

        location_encoder.fit(df['location'].unique())
        event_encoder.fit(df['event_type'].unique())

        features = []
        targets = []

        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            prev_row = df.iloc[i-1]

            # Time features
            hour = curr_row['hour']
            day_of_week = curr_row['day_of_week']

            # Previous location and event type
            prev_location_encoded = location_encoder.transform([prev_row['location']])[0]
            prev_event_type_encoded = event_encoder.transform([prev_row['event_type']])[0]

            # Time since last event (in hours)
            time_diff = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / 3600

            features.append([
                hour,
                day_of_week,
                prev_location_encoded,
                prev_event_type_encoded,
                time_diff
            ])

            targets.append(location_encoder.transform([curr_row['location']])[0])

        metadata = {
            'total_samples': len(features),
            'unique_locations': len(location_encoder.classes_),
            'unique_event_types': len(event_encoder.classes_),
            'location_encoder': location_encoder,
            'event_encoder': event_encoder
        }

        return np.array(features), np.array(targets), metadata


class AlgorithmBenchmark:
    """Benchmark different ML algorithms for location prediction"""

    def __init__(self):
        self.results = {}
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

        # Memory size
        memory_size_kb = len(pickle.dumps(model)) / 1024

        return {
            'disk_size_kb': round(disk_size_kb, 2),
            'memory_size_kb': round(memory_size_kb, 2),
            'disk_size_mb': round(disk_size_kb / 1024, 2),
            'memory_size_mb': round(memory_size_kb / 1024, 2)
        }

    def benchmark_training(self, X_train: np.ndarray, y_train: np.ndarray,
                          model: Any) -> Dict:
        """Benchmark training time and memory usage"""
        mem_before = self.get_memory_usage()

        start_time = time.perf_counter()
        model.fit(X_train, y_train)
        training_time = time.perf_counter() - start_time

        mem_after = self.get_memory_usage()
        mem_used = mem_after - mem_before

        return {
            'training_time_seconds': round(training_time, 4),
            'memory_used_mb': round(mem_used, 2),
            'memory_before_mb': round(mem_before, 2),
            'memory_after_mb': round(mem_after, 2)
        }

    def benchmark_inference(self, model: Any, X_test: np.ndarray,
                           warmup_iterations: int = 100,
                           benchmark_iterations: int = 1000) -> Dict:
        """Benchmark inference latency and throughput with statistical rigor"""
        # Warmup phase - JIT compilation, cache warming
        for _ in range(warmup_iterations):
            _ = model.predict(X_test[:10])

        # Single prediction latency benchmark
        latencies = []
        for i in range(benchmark_iterations):
            sample = X_test[i % len(X_test)].reshape(1, -1)
            start = time.perf_counter()
            _ = model.predict(sample)
            latency = (time.perf_counter() - start) * 1000  # Convert to ms
            latencies.append(latency)

        latencies = np.array(latencies)

        # Batch throughput benchmark
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
            batch_throughput[f'batch_{batch_size}'] = round(throughput, 2)

        return {
            'latency_mean_ms': round(np.mean(latencies), 4),
            'latency_median_ms': round(np.median(latencies), 4),
            'latency_p50_ms': round(np.percentile(latencies, 50), 4),
            'latency_p95_ms': round(np.percentile(latencies, 95), 4),
            'latency_p99_ms': round(np.percentile(latencies, 99), 4),
            'latency_min_ms': round(np.min(latencies), 4),
            'latency_max_ms': round(np.max(latencies), 4),
            'latency_std_ms': round(np.std(latencies), 4),
            'throughput_predictions_per_sec': round(1000 / np.mean(latencies), 2),
            'batch_throughput': batch_throughput
        }

    def benchmark_accuracy(self, model: Any, X_test: np.ndarray,
                          y_test: np.ndarray) -> Dict:
        """Benchmark prediction accuracy metrics"""
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='weighted', zero_division=0
        )

        # Top-K accuracy (if model supports probabilities)
        top_k_accuracy = {}
        if hasattr(model, 'predict_proba'):
            for k in [1, 3, 5]:
                y_proba = model.predict_proba(X_test)
                top_k_preds = np.argsort(y_proba, axis=1)[:, -k:]
                top_k_correct = np.array([y_test[i] in top_k_preds[i]
                                         for i in range(len(y_test))])
                top_k_accuracy[f'top_{k}_accuracy'] = round(np.mean(top_k_correct), 4)

        return {
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
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
        models['NeuralNetwork_Small'] = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=200,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            verbose=False
        )

        models['NeuralNetwork_Large'] = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            max_iter=200,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            verbose=False
        )

        return models

    def run_benchmark(self, n_samples: int = 5000) -> Dict:
        """Run comprehensive benchmark"""
        print("\n" + "="*80)
        print("COMPREHENSIVE ML ALGORITHM PERFORMANCE BENCHMARK")
        print("Location Prediction Task - Campus Security System")
        print("="*80)

        # Generate synthetic data
        print("\nGenerating synthetic campus security data...")
        data_gen = SyntheticDataGenerator()
        df = data_gen.generate_entity_patterns(n_samples=n_samples)

        print(f"Generated {len(df)} events across {df['location'].nunique()} locations")
        print(f"Time span: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Prepare ML features
        print("\nPreparing ML features...")
        X, y, metadata = data_gen.prepare_ml_features(df)

        print(f"Dataset: {metadata['total_samples']} samples, {metadata['unique_locations']} classes")

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"Training set: {len(X_train)} samples")
        print(f"Test set: {len(X_test)} samples")

        # Create models
        models = self.create_models()
        print(f"\nBenchmarking {len(models)} algorithms...")

        results = {}

        # Benchmark each model
        for model_name, model in models.items():
            print(f"\n{'-'*80}")
            print(f"Algorithm: {model_name}")
            print(f"{'-'*80}")

            try:
                # Training
                print("  [1/4] Training model...", end=' ', flush=True)
                training_metrics = self.benchmark_training(X_train, y_train, model)
                print(f"✓ ({training_metrics['training_time_seconds']:.3f}s)")

                # Model size
                print("  [2/4] Measuring model size...", end=' ', flush=True)
                size_metrics = self.get_model_size(model)
                print(f"✓ ({size_metrics['disk_size_kb']:.1f}KB)")

                # Accuracy
                print("  [3/4] Evaluating accuracy...", end=' ', flush=True)
                accuracy_metrics = self.benchmark_accuracy(model, X_test, y_test)
                print(f"✓ (Acc: {accuracy_metrics['accuracy']:.1%})")

                # Inference
                print("  [4/4] Benchmarking inference...", end=' ', flush=True)
                inference_metrics = self.benchmark_inference(model, X_test)
                print(f"✓ (P95: {inference_metrics['latency_p95_ms']:.4f}ms)")

                results[model_name] = {
                    **training_metrics,
                    **size_metrics,
                    **accuracy_metrics,
                    **inference_metrics,
                    'dataset_info': metadata
                }

            except Exception as e:
                print(f"✗ Failed: {str(e)}")
                results[model_name] = {'error': str(e)}

        return {
            'timestamp': datetime.now().isoformat(),
            'dataset_size': n_samples,
            'algorithms_benchmarked': len(results),
            'results': results
        }

    def generate_comparison_table(self, results: Dict) -> str:
        """Generate formatted comparison table"""
        table = []
        table.append("\n" + "="*150)
        table.append("PERFORMANCE COMPARISON TABLE - Location Prediction Algorithms")
        table.append("="*150)

        # Header
        header = (
            f"{'Algorithm':<25} {'Accuracy':<12} {'P95 Latency':<15} {'Throughput':<18} "
            f"{'Model Size':<15} {'Train Time':<15}"
        )
        table.append(header)
        table.append("-"*150)

        # Baseline reference
        baseline_metrics = results['results'].get('RandomForest', {})

        # Rows
        for model_name in sorted(results['results'].keys()):
            metrics = results['results'][model_name]

            if 'error' in metrics:
                table.append(f"{model_name:<25} ERROR: {metrics['error']}")
                continue

            accuracy = metrics.get('accuracy', 0)
            latency_p95 = metrics.get('latency_p95_ms', 0)
            throughput = metrics.get('throughput_predictions_per_sec', 0)
            model_size = metrics.get('disk_size_kb', 0)
            training_time = metrics.get('training_time_seconds', 0)

            # Calculate improvements vs baseline
            if baseline_metrics and model_name != 'RandomForest':
                acc_diff = ((accuracy / baseline_metrics.get('accuracy', 1)) - 1) * 100
                lat_diff = ((latency_p95 / baseline_metrics.get('latency_p95_ms', 1)) - 1) * 100
                acc_indicator = f"({acc_diff:+.1f}%)" if abs(acc_diff) > 0.1 else ""
                lat_indicator = f"({lat_diff:+.1f}%)" if abs(lat_diff) > 0.1 else ""
            else:
                acc_indicator = "(baseline)"
                lat_indicator = "(baseline)"

            row = (
                f"{model_name:<25} {accuracy:>7.1%} {acc_indicator:<4} "
                f"{latency_p95:>9.4f} ms {lat_indicator:<9} "
                f"{throughput:>10.0f} pred/s   "
                f"{model_size:>9.1f} KB   "
                f"{training_time:>10.3f} s"
            )
            table.append(row)

        table.append("="*150)
        table.append("\nKey Metrics Explained:")
        table.append("- Accuracy: Overall prediction accuracy on test set")
        table.append("- P95 Latency: 95th percentile single prediction latency (lower is better)")
        table.append("- Throughput: Predictions per second for single predictions")
        table.append("- Model Size: Serialized model size on disk (31 models × size = total memory)")
        table.append("- Train Time: Time to train model on training set")

        return "\n".join(table)

    def generate_recommendation(self, results: Dict) -> str:
        """Generate production deployment recommendation"""
        algo_results = results['results']

        # Score each algorithm based on requirements
        scores = {}
        for model_name, metrics in algo_results.items():
            if 'error' in metrics:
                continue

            score = 0

            # Accuracy (40% weight) - most important for user experience
            accuracy = metrics.get('accuracy', 0)
            score += accuracy * 40

            # Latency (25% weight) - <10ms requirement easily met
            latency = metrics.get('latency_p95_ms', 0)
            if latency < 1:  # Excellent
                latency_score = 1.0
            elif latency < 5:  # Good
                latency_score = 0.8
            else:  # Acceptable
                latency_score = 0.5
            score += latency_score * 25

            # Model size (25% weight) - 31 models need to fit in memory
            size_mb = metrics.get('disk_size_mb', 0)
            total_size_mb = size_mb * 31
            if total_size_mb < 20:  # Excellent
                size_score = 1.0
            elif total_size_mb < 50:  # Good
                size_score = 0.7
            else:  # Acceptable
                size_score = 0.4
            score += size_score * 25

            # Training time (10% weight) - can train overnight
            train_time = metrics.get('training_time_seconds', 0)
            if train_time < 1:  # Very fast
                train_score = 1.0
            elif train_time < 10:  # Fast enough
                train_score = 0.8
            else:  # Slower but acceptable
                train_score = 0.5
            score += train_score * 10

            scores[model_name] = score

        # Rank algorithms
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        recommendation = []
        recommendation.append("\n" + "="*80)
        recommendation.append("PRODUCTION DEPLOYMENT RECOMMENDATION")
        recommendation.append("="*80)

        recommendation.append("\nContext: Campus Security Location Prediction System")
        recommendation.append("Requirements:")
        recommendation.append("  - Prediction latency <10ms (real-time not critical)")
        recommendation.append("  - High accuracy important (poor predictions = bad UX)")
        recommendation.append("  - 31 models must fit in memory")
        recommendation.append("  - Training time <1 hour acceptable (overnight training)")

        recommendation.append("\n" + "-"*80)
        recommendation.append("ALGORITHM RANKINGS (Weighted Score: Accuracy 40%, Latency 25%, Size 25%, Training 10%)")
        recommendation.append("-"*80)

        for i, (model_name, score) in enumerate(ranked[:5], 1):
            metrics = algo_results[model_name]
            accuracy = metrics.get('accuracy', 0)
            latency = metrics.get('latency_p95_ms', 0)
            size_kb = metrics.get('disk_size_kb', 0)
            train_time = metrics.get('training_time_seconds', 0)
            throughput = metrics.get('throughput_predictions_per_sec', 0)

            total_size_mb = size_kb * 31 / 1024

            recommendation.append(f"\n{i}. {model_name} - Overall Score: {score:.1f}/100")
            recommendation.append(f"   Accuracy:     {accuracy:.2%}")
            recommendation.append(f"   P95 Latency:  {latency:.4f} ms")
            recommendation.append(f"   Throughput:   {throughput:.0f} predictions/sec")
            recommendation.append(f"   Model Size:   {size_kb:.1f} KB per model ({total_size_mb:.1f} MB total for 31 models)")
            recommendation.append(f"   Train Time:   {train_time:.3f} seconds")

        # Winner analysis
        winner = ranked[0][0]
        winner_metrics = algo_results[winner]

        recommendation.append("\n" + "="*80)
        recommendation.append(f"RECOMMENDED: {winner}")
        recommendation.append("="*80)

        accuracy = winner_metrics.get('accuracy', 0)
        latency_p95 = winner_metrics.get('latency_p95_ms', 0)
        size_kb = winner_metrics.get('disk_size_kb', 0)
        train_time = winner_metrics.get('training_time_seconds', 0)
        throughput = winner_metrics.get('throughput_predictions_per_sec', 0)
        total_size = size_kb * 31 / 1024

        recommendation.append(f"\nPerformance Summary:")
        recommendation.append(f"  ✓ Accuracy: {accuracy:.2%} - {self._accuracy_assessment(accuracy)}")
        recommendation.append(f"  ✓ Latency: {latency_p95:.4f}ms P95 - {self._latency_assessment(latency_p95)}")
        recommendation.append(f"  ✓ Throughput: {throughput:.0f} predictions/sec - {self._throughput_assessment(throughput)}")
        recommendation.append(f"  ✓ Memory: {total_size:.1f}MB total - {self._memory_assessment(total_size)}")
        recommendation.append(f"  ✓ Training: {train_time:.2f}s per model ({train_time * 31 / 60:.1f} min for all 31) - {self._training_assessment(train_time * 31)}")

        # Comparison with baseline
        if 'RandomForest' in algo_results and winner != 'RandomForest':
            rf_metrics = algo_results['RandomForest']
            recommendation.append(f"\nComparison with RandomForest (current baseline):")

            acc_change = ((accuracy / rf_metrics.get('accuracy', 1)) - 1) * 100
            lat_change = ((latency_p95 / rf_metrics.get('latency_p95_ms', 1)) - 1) * 100
            size_change = ((size_kb / rf_metrics.get('disk_size_kb', 1)) - 1) * 100
            train_change = ((train_time / rf_metrics.get('training_time_seconds', 1)) - 1) * 100

            recommendation.append(f"  Accuracy:      {acc_change:+.1f}%")
            recommendation.append(f"  Latency:       {lat_change:+.1f}% (lower is better)")
            recommendation.append(f"  Model Size:    {size_change:+.1f}% (lower is better)")
            recommendation.append(f"  Training Time: {train_change:+.1f}% (lower is better)")

            # ROI Analysis
            recommendation.append(f"\nMigration ROI Analysis:")
            if acc_change > 0:
                recommendation.append(f"  + {acc_change:.1f}% accuracy improvement = better user experience")
            if size_change < 0:
                memory_saved = (rf_metrics.get('disk_size_kb', 0) - size_kb) * 31 / 1024
                recommendation.append(f"  + {abs(size_change):.1f}% smaller models = {memory_saved:.1f}MB memory saved")
            if lat_change < 0:
                recommendation.append(f"  + {abs(lat_change):.1f}% faster inference = better responsiveness")

        recommendation.append("\n" + "="*80)

        return "\n".join(recommendation)

    def _accuracy_assessment(self, accuracy: float) -> str:
        if accuracy > 0.85:
            return "Excellent for production"
        elif accuracy > 0.75:
            return "Good for production"
        elif accuracy > 0.65:
            return "Acceptable but could be improved"
        else:
            return "Below production standards"

    def _latency_assessment(self, latency_ms: float) -> str:
        if latency_ms < 1:
            return "Excellent, real-time capable"
        elif latency_ms < 5:
            return "Very good, well within requirements"
        elif latency_ms < 10:
            return "Good, meets <10ms requirement"
        else:
            return "Acceptable but above ideal threshold"

    def _throughput_assessment(self, throughput: float) -> str:
        if throughput > 5000:
            return "Excellent throughput for high load"
        elif throughput > 1000:
            return "Good throughput for typical load"
        elif throughput > 500:
            return "Adequate for moderate load"
        else:
            return "May need optimization for high load"

    def _memory_assessment(self, total_mb: float) -> str:
        if total_mb < 20:
            return "Excellent memory efficiency"
        elif total_mb < 50:
            return "Good memory usage"
        elif total_mb < 100:
            return "Acceptable memory footprint"
        else:
            return "High memory usage, consider optimization"

    def _training_assessment(self, total_seconds: float) -> str:
        if total_seconds < 60:
            return "Very fast, can retrain frequently"
        elif total_seconds < 600:
            return "Fast enough for regular retraining"
        elif total_seconds < 3600:
            return "Acceptable for overnight retraining"
        else:
            return "Slow training, limits retraining frequency"

    def save_results(self, results: Dict):
        """Save benchmark results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # JSON results
        json_path = self.benchmark_dir / f'benchmark_results_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Formatted report
        report_path = self.benchmark_dir / f'benchmark_report_{timestamp}.txt'
        with open(report_path, 'w') as f:
            f.write(self.generate_comparison_table(results))
            f.write("\n\n")
            f.write(self.generate_recommendation(results))

        print(f"\n\nResults saved:")
        print(f"  JSON: {json_path}")
        print(f"  Report: {report_path}")

        return json_path, report_path


def main():
    """Run comprehensive benchmark"""
    benchmark = AlgorithmBenchmark()

    # Run with 5000 samples (representative of real-world dataset)
    results = benchmark.run_benchmark(n_samples=5000)

    # Print comparison table
    print(benchmark.generate_comparison_table(results))

    # Print recommendation
    print(benchmark.generate_recommendation(results))

    # Save results
    benchmark.save_results(results)


if __name__ == "__main__":
    main()
