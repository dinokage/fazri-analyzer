"""
Machine Learning Performance Benchmarking Suite for Fazri Analyzer
Comprehensive performance analysis of ML model loading, inference, and scalability
"""

import sys
import time
import pickle
import psutil
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from collections import defaultdict

sys.path.append(str(Path(__file__).parent))

from services.ml_predictor import LocationPredictor
from services.entity_resolver import EntityResolver
from services.anomaly_detection import AnomalyDetectionService
from services.entity_anomaly_detection import EntityAnomalyDetectionService

class MLPerformanceBenchmark:
    """Comprehensive ML performance benchmarking suite"""

    def __init__(self):
        self.results = {
            'model_loading': {},
            'inference': {},
            'resource_utilization': {},
            'scalability': {},
            'optimization_opportunities': [],
            'benchmark_metadata': {
                'timestamp': datetime.now().isoformat(),
                'system_info': self._get_system_info()
            }
        }
        self.models_dir = Path(__file__).parent / 'models'
        self.data_dir = Path(__file__).parent / 'augmented'

    def _get_system_info(self) -> Dict:
        """Gather system information"""
        return {
            'cpu_count': psutil.cpu_count(logical=True),
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'available_memory_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'python_version': sys.version.split()[0]
        }

    def _measure_memory(self) -> Dict:
        """Measure current memory usage"""
        process = psutil.Process()
        return {
            'rss_mb': round(process.memory_info().rss / (1024**2), 2),
            'vms_mb': round(process.memory_info().vms / (1024**2), 2),
            'percent': round(process.memory_percent(), 2)
        }

    def benchmark_model_loading(self) -> Dict:
        """
        Benchmark 1: Model Loading Performance
        - Time to load 31 pickle files
        - Memory footprint of loaded models
        - Cold start vs warm start performance
        """
        print("\n" + "="*80)
        print("BENCHMARK 1: Model Loading Performance")
        print("="*80)

        model_files = list(self.models_dir.glob('predictor_*.pkl'))
        print(f"\nFound {len(model_files)} model files")

        # Get total size of all models
        total_size_mb = sum(f.stat().st_size for f in model_files) / (1024**2)
        print(f"Total models size: {total_size_mb:.2f} MB")

        # Cold start - load all models
        memory_before = self._measure_memory()
        start_time = time.time()

        models = {}
        load_times = []

        for model_file in model_files:
            file_start = time.time()
            try:
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                    models[model_file.stem] = model_data
                file_time = time.time() - file_start
                load_times.append(file_time)
            except Exception as e:
                print(f"Error loading {model_file.name}: {e}")

        total_load_time = time.time() - start_time
        memory_after = self._measure_memory()

        # Calculate memory increase
        memory_increase_mb = memory_after['rss_mb'] - memory_before['rss_mb']

        cold_start_results = {
            'total_models': len(models),
            'total_load_time_seconds': round(total_load_time, 3),
            'avg_load_time_ms': round(np.mean(load_times) * 1000, 2),
            'median_load_time_ms': round(np.median(load_times) * 1000, 2),
            'p95_load_time_ms': round(np.percentile(load_times, 95) * 1000, 2),
            'min_load_time_ms': round(min(load_times) * 1000, 2),
            'max_load_time_ms': round(max(load_times) * 1000, 2),
            'models_per_second': round(len(models) / total_load_time, 2),
            'total_size_mb': round(total_size_mb, 2),
            'memory_increase_mb': round(memory_increase_mb, 2),
            'memory_per_model_kb': round((memory_increase_mb * 1024) / len(models), 2)
        }

        print(f"\nCold Start Results:")
        print(f"  Total load time: {cold_start_results['total_load_time_seconds']:.3f}s")
        print(f"  Average per model: {cold_start_results['avg_load_time_ms']:.2f}ms")
        print(f"  Throughput: {cold_start_results['models_per_second']:.2f} models/sec")
        print(f"  Memory increase: {cold_start_results['memory_increase_mb']:.2f} MB")
        print(f"  Memory per model: {cold_start_results['memory_per_model_kb']:.2f} KB")

        # Warm start - reload same models
        reload_times = []
        start_time = time.time()

        for model_file in model_files[:10]:  # Test 10 models for warm start
            file_start = time.time()
            with open(model_file, 'rb') as f:
                pickle.load(f)
            reload_times.append(time.time() - file_start)

        warm_start_time = time.time() - start_time

        warm_start_results = {
            'sample_size': len(reload_times),
            'total_time_seconds': round(warm_start_time, 3),
            'avg_load_time_ms': round(np.mean(reload_times) * 1000, 2),
            'speedup_vs_cold': round(cold_start_results['avg_load_time_ms'] / (np.mean(reload_times) * 1000), 2)
        }

        print(f"\nWarm Start Results (10 models):")
        print(f"  Average load time: {warm_start_results['avg_load_time_ms']:.2f}ms")
        print(f"  Speedup vs cold: {warm_start_results['speedup_vs_cold']:.2f}x")

        self.results['model_loading'] = {
            'cold_start': cold_start_results,
            'warm_start': warm_start_results,
            'loaded_models': models
        }

        return models

    def benchmark_inference_performance(self, models: Dict) -> Dict:
        """
        Benchmark 2: Inference Performance
        - Prediction latency for entity resolution
        - Batch vs single prediction efficiency
        - Throughput (predictions per second)
        """
        print("\n" + "="*80)
        print("BENCHMARK 2: Inference Performance")
        print("="*80)

        if not models:
            print("No models loaded for inference testing")
            return {}

        # Select a sample model
        sample_model_key = list(models.keys())[0]
        sample_model = models[sample_model_key]

        predictor = LocationPredictor()
        predictor.model = sample_model['model']
        predictor.location_encoder = sample_model['location_encoder']
        predictor.event_encoder = sample_model['event_encoder']
        predictor.feature_importance = sample_model['feature_importance']
        predictor.is_trained = True

        # Generate synthetic test data
        test_events = self._generate_test_events(100)
        target_time = datetime.now() + timedelta(hours=1)

        # Single prediction latency
        single_prediction_times = []
        for _ in range(100):
            start = time.time()
            predictor.predict(target_time, test_events[:20], top_k=3)
            single_prediction_times.append(time.time() - start)

        single_pred_results = {
            'avg_latency_ms': round(np.mean(single_prediction_times) * 1000, 2),
            'median_latency_ms': round(np.median(single_prediction_times) * 1000, 2),
            'p95_latency_ms': round(np.percentile(single_prediction_times, 95) * 1000, 2),
            'p99_latency_ms': round(np.percentile(single_prediction_times, 99) * 1000, 2),
            'min_latency_ms': round(min(single_prediction_times) * 1000, 2),
            'max_latency_ms': round(max(single_prediction_times) * 1000, 2),
            'throughput_per_sec': round(1 / np.mean(single_prediction_times), 2)
        }

        print(f"\nSingle Prediction Performance:")
        print(f"  Average latency: {single_pred_results['avg_latency_ms']:.2f}ms")
        print(f"  P95 latency: {single_pred_results['p95_latency_ms']:.2f}ms")
        print(f"  P99 latency: {single_pred_results['p99_latency_ms']:.2f}ms")
        print(f"  Throughput: {single_pred_results['throughput_per_sec']:.2f} predictions/sec")

        # Batch prediction performance
        batch_sizes = [1, 10, 50, 100]
        batch_results = {}

        for batch_size in batch_sizes:
            batch_times = []
            for _ in range(20):
                start = time.time()
                for i in range(batch_size):
                    predictor.predict(target_time, test_events[:20], top_k=3)
                batch_times.append(time.time() - start)

            avg_batch_time = np.mean(batch_times)
            avg_per_item = avg_batch_time / batch_size

            batch_results[f'batch_{batch_size}'] = {
                'batch_size': batch_size,
                'avg_total_time_ms': round(avg_batch_time * 1000, 2),
                'avg_per_item_ms': round(avg_per_item * 1000, 2),
                'throughput_per_sec': round(batch_size / avg_batch_time, 2)
            }

        print(f"\nBatch Prediction Performance:")
        for batch_key, batch_data in batch_results.items():
            print(f"  Batch size {batch_data['batch_size']}:")
            print(f"    Per-item latency: {batch_data['avg_per_item_ms']:.2f}ms")
            print(f"    Throughput: {batch_data['throughput_per_sec']:.2f} predictions/sec")

        # Entity resolution performance (skip if data not available)
        resolution_results = {}
        try:
            print(f"\nEntity Resolution Performance:")
            resolver_start = time.time()
            resolver = EntityResolver(self.data_dir)
            resolver.build_entity_graph()
            resolution_build_time = time.time() - resolver_start

            # Test resolution speed
            resolution_times = []
            test_identifiers = [
                ('card_id', 'C123456'),
                ('email', 'test@example.com'),
                ('entity_id', 'E100001')
            ]

            for id_type, id_value in test_identifiers * 100:
                start = time.time()
                resolver.resolve_by_identifier(id_type, id_value)
                resolution_times.append(time.time() - start)

            resolution_results = {
                'graph_build_time_seconds': round(resolution_build_time, 3),
                'entities_indexed': len(resolver.entities),
                'identifiers_indexed': len(resolver.identifier_index),
                'avg_resolution_time_us': round(np.mean(resolution_times) * 1_000_000, 2),
                'p95_resolution_time_us': round(np.percentile(resolution_times, 95) * 1_000_000, 2),
                'throughput_per_sec': round(1 / np.mean(resolution_times), 0)
            }

            print(f"  Graph build time: {resolution_results['graph_build_time_seconds']:.3f}s")
            print(f"  Entities indexed: {resolution_results['entities_indexed']}")
            print(f"  Avg resolution time: {resolution_results['avg_resolution_time_us']:.2f}μs")
            print(f"  Throughput: {resolution_results['throughput_per_sec']:.0f} resolutions/sec")
        except Exception as e:
            print(f"  Skipped (data not available): {e}")
            resolution_results = {'status': 'skipped', 'reason': str(e)}

        self.results['inference'] = {
            'single_prediction': single_pred_results,
            'batch_prediction': batch_results,
            'entity_resolution': resolution_results
        }

        return self.results['inference']

    def benchmark_resource_utilization(self) -> Dict:
        """
        Benchmark 3: Resource Utilization
        - CPU usage during inference
        - Memory consumption patterns
        - I/O bottlenecks
        """
        print("\n" + "="*80)
        print("BENCHMARK 3: Resource Utilization")
        print("="*80)

        # Monitor CPU and memory during sustained load
        cpu_samples = []
        memory_samples = []

        def monitor_resources(duration_seconds=5):
            """Monitor CPU and memory for specified duration"""
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                cpu_samples.append(psutil.cpu_percent(interval=0.1))
                memory_samples.append(psutil.virtual_memory().percent)
                time.sleep(0.1)

        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_resources, args=(5,))
        monitor_thread.start()

        # Generate load
        model_files = list(self.models_dir.glob('predictor_*.pkl'))[:5]
        test_events = self._generate_test_events(50)
        target_time = datetime.now() + timedelta(hours=1)

        for model_file in model_files:
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)

            predictor = LocationPredictor()
            predictor.model = model_data['model']
            predictor.location_encoder = model_data['location_encoder']
            predictor.event_encoder = model_data['event_encoder']
            predictor.feature_importance = model_data['feature_importance']
            predictor.is_trained = True

            for _ in range(20):
                predictor.predict(target_time, test_events[:20], top_k=3)

        monitor_thread.join()

        resource_results = {
            'cpu_utilization': {
                'avg_percent': round(np.mean(cpu_samples), 2),
                'max_percent': round(max(cpu_samples), 2),
                'min_percent': round(min(cpu_samples), 2)
            },
            'memory_utilization': {
                'avg_percent': round(np.mean(memory_samples), 2),
                'max_percent': round(max(memory_samples), 2),
                'current_process_mb': self._measure_memory()['rss_mb']
            },
            'io_characteristics': {
                'model_files_count': len(model_files),
                'avg_file_size_kb': round(sum(f.stat().st_size for f in model_files) / len(model_files) / 1024, 2)
            }
        }

        print(f"\nCPU Utilization:")
        print(f"  Average: {resource_results['cpu_utilization']['avg_percent']:.2f}%")
        print(f"  Peak: {resource_results['cpu_utilization']['max_percent']:.2f}%")

        print(f"\nMemory Utilization:")
        print(f"  Average: {resource_results['memory_utilization']['avg_percent']:.2f}%")
        print(f"  Process RSS: {resource_results['memory_utilization']['current_process_mb']:.2f} MB")

        self.results['resource_utilization'] = resource_results
        return resource_results

    def benchmark_scalability(self, models: Dict) -> Dict:
        """
        Benchmark 4: Scalability Analysis
        - Concurrent request handling
        - Model serving under load
        - Horizontal scaling possibilities
        """
        print("\n" + "="*80)
        print("BENCHMARK 4: Scalability Analysis")
        print("="*80)

        if not models:
            print("No models loaded for scalability testing")
            return {}

        sample_model = models[list(models.keys())[0]]
        test_events = self._generate_test_events(50)
        target_time = datetime.now() + timedelta(hours=1)

        def make_prediction():
            """Single prediction task"""
            predictor = LocationPredictor()
            predictor.model = sample_model['model']
            predictor.location_encoder = sample_model['location_encoder']
            predictor.event_encoder = sample_model['event_encoder']
            predictor.feature_importance = sample_model['feature_importance']
            predictor.is_trained = True

            start = time.time()
            predictor.predict(target_time, test_events[:20], top_k=3)
            return time.time() - start

        # Test concurrent requests with different thread counts
        thread_counts = [1, 2, 4, 8, 16]
        scalability_results = {}

        for thread_count in thread_counts:
            print(f"\nTesting with {thread_count} concurrent threads...")

            start_time = time.time()
            latencies = []

            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(make_prediction) for _ in range(100)]

                for future in as_completed(futures):
                    try:
                        latency = future.result()
                        latencies.append(latency)
                    except Exception as e:
                        print(f"Error in thread: {e}")

            total_time = time.time() - start_time

            scalability_results[f'threads_{thread_count}'] = {
                'thread_count': thread_count,
                'total_requests': len(latencies),
                'total_time_seconds': round(total_time, 3),
                'avg_latency_ms': round(np.mean(latencies) * 1000, 2),
                'p95_latency_ms': round(np.percentile(latencies, 95) * 1000, 2),
                'p99_latency_ms': round(np.percentile(latencies, 99) * 1000, 2),
                'throughput_per_sec': round(len(latencies) / total_time, 2),
                'requests_per_thread_per_sec': round(len(latencies) / total_time / thread_count, 2)
            }

            print(f"  Throughput: {scalability_results[f'threads_{thread_count}']['throughput_per_sec']:.2f} req/sec")
            print(f"  P95 latency: {scalability_results[f'threads_{thread_count}']['p95_latency_ms']:.2f}ms")

        # Calculate scalability efficiency
        baseline_throughput = scalability_results['threads_1']['throughput_per_sec']

        for key, data in scalability_results.items():
            expected_throughput = baseline_throughput * data['thread_count']
            actual_throughput = data['throughput_per_sec']
            data['scalability_efficiency'] = round((actual_throughput / expected_throughput) * 100, 2)

        print(f"\nScalability Efficiency:")
        for key, data in scalability_results.items():
            print(f"  {data['thread_count']} threads: {data['scalability_efficiency']:.2f}% efficient")

        self.results['scalability'] = scalability_results
        return scalability_results

    def analyze_optimization_opportunities(self) -> List[Dict]:
        """
        Identify optimization opportunities based on benchmark results
        """
        print("\n" + "="*80)
        print("OPTIMIZATION OPPORTUNITIES ANALYSIS")
        print("="*80)

        opportunities = []

        # Model loading optimizations
        if 'model_loading' in self.results:
            cold_start = self.results['model_loading']['cold_start']

            if cold_start['total_load_time_seconds'] > 5:
                opportunities.append({
                    'category': 'Model Loading',
                    'issue': 'High cold start time',
                    'metric': f"{cold_start['total_load_time_seconds']:.2f}s for {cold_start['total_models']} models",
                    'impact': 'Critical - affects application startup time',
                    'recommendations': [
                        'Implement lazy loading - load models on-demand',
                        'Use model compression (joblib with compression)',
                        'Consider model caching in Redis/Memcached',
                        'Pre-load only frequently used models',
                        'Use multiprocessing for parallel model loading'
                    ],
                    'expected_improvement': '60-80% reduction in startup time'
                })

            if cold_start['memory_increase_mb'] > 500:
                opportunities.append({
                    'category': 'Memory Optimization',
                    'issue': 'High memory footprint',
                    'metric': f"{cold_start['memory_increase_mb']:.2f} MB for {cold_start['total_models']} models",
                    'impact': 'High - limits concurrent capacity',
                    'recommendations': [
                        'Implement model quantization',
                        'Use sparse model representations',
                        'Share common encoders across models',
                        'Implement LRU cache for models with TTL',
                        'Consider model pruning for RandomForest (reduce trees)'
                    ],
                    'expected_improvement': '40-60% memory reduction'
                })

        # Inference optimizations
        if 'inference' in self.results and 'single_prediction' in self.results['inference']:
            single_pred = self.results['inference']['single_prediction']

            if single_pred['p95_latency_ms'] > 100:
                opportunities.append({
                    'category': 'Inference Performance',
                    'issue': 'High prediction latency',
                    'metric': f"P95: {single_pred['p95_latency_ms']:.2f}ms",
                    'impact': 'High - affects user experience',
                    'recommendations': [
                        'Implement prediction result caching',
                        'Use batch prediction API for multiple requests',
                        'Pre-compute predictions for common scenarios',
                        'Optimize feature extraction pipeline',
                        'Consider ONNX conversion for faster inference'
                    ],
                    'expected_improvement': '50-70% latency reduction'
                })

            # Batch processing efficiency
            if 'batch_prediction' in self.results['inference']:
                batch_results = self.results['inference']['batch_prediction']
                batch_1 = batch_results['batch_1']['throughput_per_sec']
                batch_100 = batch_results['batch_100']['throughput_per_sec']

                if batch_100 < batch_1 * 50:  # Less than 50x improvement with 100x batch
                    opportunities.append({
                        'category': 'Batch Processing',
                        'issue': 'Inefficient batch processing',
                        'metric': f"100x batch only {batch_100/batch_1:.1f}x faster",
                        'impact': 'Medium - affects bulk processing',
                        'recommendations': [
                            'Vectorize feature extraction',
                            'Use NumPy broadcasting for batch operations',
                            'Implement GPU acceleration for batch predictions',
                            'Optimize encoder transform for batch inputs'
                        ],
                        'expected_improvement': '3-5x batch throughput increase'
                    })

        # Scalability optimizations
        if 'scalability' in self.results:
            threads_8 = self.results['scalability'].get('threads_8', {})

            if threads_8 and threads_8.get('scalability_efficiency', 100) < 50:
                opportunities.append({
                    'category': 'Concurrency',
                    'issue': 'Poor scaling efficiency',
                    'metric': f"{threads_8['scalability_efficiency']:.1f}% efficient at 8 threads",
                    'impact': 'Critical - limits production capacity',
                    'recommendations': [
                        'Remove GIL bottlenecks - use multiprocessing instead of threading',
                        'Implement async inference with asyncio',
                        'Use model server (TorchServe, TensorFlow Serving)',
                        'Deploy models behind load balancer',
                        'Consider horizontal pod autoscaling in Kubernetes'
                    ],
                    'expected_improvement': 'Near-linear scaling up to core count'
                })

        # Resource utilization optimizations
        if 'resource_utilization' in self.results:
            cpu_util = self.results['resource_utilization']['cpu_utilization']

            if cpu_util['avg_percent'] < 30:
                opportunities.append({
                    'category': 'Resource Utilization',
                    'issue': 'Low CPU utilization',
                    'metric': f"{cpu_util['avg_percent']:.1f}% average CPU usage",
                    'impact': 'Medium - underutilized resources',
                    'recommendations': [
                        'Increase concurrent request processing',
                        'Implement CPU-intensive preprocessing in parallel',
                        'Use process pool for CPU-bound tasks',
                        'Enable multi-threaded inference in scikit-learn'
                    ],
                    'expected_improvement': '2-3x throughput with same resources'
                })

        # Print opportunities
        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. {opp['category']}: {opp['issue']}")
            print(f"   Metric: {opp['metric']}")
            print(f"   Impact: {opp['impact']}")
            print(f"   Recommendations:")
            for rec in opp['recommendations']:
                print(f"     - {rec}")
            print(f"   Expected Improvement: {opp['expected_improvement']}")

        self.results['optimization_opportunities'] = opportunities
        return opportunities

    def _generate_test_events(self, count: int) -> List[Dict]:
        """Generate synthetic test events for benchmarking"""
        locations = ['LAB_101', 'LIB_ENT', 'CAF_01', 'GYM', 'AUDITORIUM']
        event_types = ['entry', 'exit', 'swipe']

        base_time = datetime.now() - timedelta(days=30)
        events = []

        for i in range(count):
            events.append({
                'timestamp': base_time + timedelta(hours=i),
                'location': np.random.choice(locations),
                'event_type': np.random.choice(event_types),
                'entity_id': 'E100001'
            })

        return events

    def generate_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("="*80)

        # Summary statistics
        if 'model_loading' in self.results:
            cold_start = self.results['model_loading']['cold_start']
            print(f"\nModel Loading:")
            print(f"  Total models: {cold_start['total_models']}")
            print(f"  Load time: {cold_start['total_load_time_seconds']:.3f}s")
            print(f"  Memory footprint: {cold_start['memory_increase_mb']:.2f} MB")

        if 'inference' in self.results:
            single_pred = self.results['inference'].get('single_prediction', {})
            if single_pred:
                print(f"\nInference Performance:")
                print(f"  Average latency: {single_pred['avg_latency_ms']:.2f}ms")
                print(f"  P95 latency: {single_pred['p95_latency_ms']:.2f}ms")
                print(f"  Throughput: {single_pred['throughput_per_sec']:.2f} predictions/sec")

        if 'scalability' in self.results:
            threads_8 = self.results['scalability'].get('threads_8', {})
            if threads_8:
                print(f"\nScalability (8 threads):")
                print(f"  Throughput: {threads_8['throughput_per_sec']:.2f} req/sec")
                print(f"  Efficiency: {threads_8['scalability_efficiency']:.1f}%")

        print(f"\nOptimization Opportunities: {len(self.results.get('optimization_opportunities', []))}")

        # Save detailed results
        output_file = Path(__file__).parent / 'ml_performance_benchmark_results.json'
        with open(output_file, 'w') as f:
            # Convert numpy types to native Python types for JSON serialization
            json_results = json.loads(json.dumps(self.results, default=str))
            json.dump(json_results, f, indent=2, default=str)

        print(f"\nDetailed results saved to: {output_file}")

        return self.results

    def run_full_benchmark(self):
        """Run complete benchmark suite"""
        print("\n" + "="*80)
        print("FAZRI ANALYZER - ML PERFORMANCE BENCHMARK SUITE")
        print("="*80)
        print(f"\nSystem Information:")
        print(f"  CPU Cores: {self.results['benchmark_metadata']['system_info']['cpu_count']}")
        print(f"  Memory: {self.results['benchmark_metadata']['system_info']['total_memory_gb']:.2f} GB")

        # Run all benchmarks
        models = self.benchmark_model_loading()
        self.benchmark_inference_performance(models)
        self.benchmark_resource_utilization()
        self.benchmark_scalability(models)
        self.analyze_optimization_opportunities()

        # Generate final report
        self.generate_report()

def main():
    """Main execution function"""
    benchmark = MLPerformanceBenchmark()
    benchmark.run_full_benchmark()

if __name__ == "__main__":
    main()
