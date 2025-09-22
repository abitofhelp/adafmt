# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Performance benchmarking for optimal worker count determination."""

import time
import os
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .thread_safe_metrics import ThreadSafeMetrics
from .logging_jsonl import JsonlLogger


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    worker_count: int
    total_files: int
    total_time: float
    files_per_second: float
    avg_queue_wait: float
    avg_pattern_time: float
    avg_io_time: float
    errors: int
    cpu_count: int
    memory_mb: float
    
    def __str__(self) -> str:
        """Format result as string."""
        return (
            f"Workers: {self.worker_count:2d} | "
            f"Time: {self.total_time:6.2f}s | "
            f"Rate: {self.files_per_second:6.1f} files/s | "
            f"Queue wait: {self.avg_queue_wait*1000:5.1f}ms | "
            f"Pattern: {self.avg_pattern_time*1000:5.1f}ms | "
            f"I/O: {self.avg_io_time*1000:5.1f}ms | "
            f"Errors: {self.errors}"
        )


class PerformanceBenchmark:
    """Benchmark different worker configurations."""
    
    def __init__(
        self,
        logger: Optional[JsonlLogger] = None,
        warmup_files: int = 10
    ):
        """Initialize benchmark.
        
        Args:
            logger: Optional logger for results
            warmup_files: Number of files for warmup runs
        """
        self.logger = logger
        self.warmup_files = warmup_files
        self.cpu_count = os.cpu_count() or 4
    
    async def benchmark_worker_count(
        self,
        worker_counts: List[int],
        file_paths: List[Path],
        file_processor,
        runs_per_config: int = 3
    ) -> Dict[int, BenchmarkResult]:
        """Benchmark different worker counts.
        
        Args:
            worker_counts: List of worker counts to test
            file_paths: Files to process
            file_processor: File processor instance
            runs_per_config: Number of runs per configuration
            
        Returns:
            Dictionary of worker_count -> BenchmarkResult
        """
        results = {}
        
        # Save original worker count
        original_workers = file_processor.num_workers
        
        try:
            for worker_count in worker_counts:
                print(f"\nBenchmarking with {worker_count} workers...")
                
                # Run warmup if first configuration
                if worker_count == worker_counts[0] and self.warmup_files > 0:
                    await self._run_warmup(
                        file_processor,
                        file_paths[:self.warmup_files],
                        worker_count
                    )
                
                # Collect multiple runs
                run_times = []
                run_metrics = []
                
                for run in range(runs_per_config):
                    print(f"  Run {run + 1}/{runs_per_config}...")
                    
                    # Reset metrics
                    metrics = ThreadSafeMetrics()
                    
                    # Configure processor
                    file_processor.num_workers = worker_count
                    file_processor.thread_safe_metrics = metrics
                    
                    # Initialize worker pool
                    await file_processor.initialize_worker_pool()
                    
                    # Process files
                    start_time = time.time()
                    
                    for idx, path in enumerate(file_paths):
                        status, _ = await file_processor.process_file(
                            path, idx + 1, len(file_paths), start_time
                        )
                    
                    # Shutdown and collect metrics
                    await file_processor.shutdown_worker_pool()
                    
                    total_time = time.time() - start_time
                    snapshot = await metrics.get_snapshot()
                    
                    run_times.append(total_time)
                    run_metrics.append(snapshot)
                
                # Calculate average results
                avg_time = statistics.mean(run_times)
                avg_metrics = self._average_metrics(run_metrics)
                
                # Create result
                result = BenchmarkResult(
                    worker_count=worker_count,
                    total_files=len(file_paths),
                    total_time=avg_time,
                    files_per_second=len(file_paths) / avg_time,
                    avg_queue_wait=avg_metrics['queue_wait_time'] / max(1, avg_metrics['total_processed']),
                    avg_pattern_time=avg_metrics['pattern_time'] / max(1, avg_metrics['total_processed']),
                    avg_io_time=avg_metrics['io_time'] / max(1, avg_metrics['total_processed']),
                    errors=avg_metrics['errors'],
                    cpu_count=self.cpu_count,
                    memory_mb=self._get_memory_usage_mb()
                )
                
                results[worker_count] = result
                print(f"  {result}")
                
                # Log result
                if self.logger:
                    self.logger.write({
                        'ev': 'benchmark_result',
                        'worker_count': worker_count,
                        'total_files': len(file_paths),
                        'avg_time': avg_time,
                        'files_per_second': result.files_per_second,
                        'runs': runs_per_config
                    })
        
        finally:
            # Restore original worker count
            file_processor.num_workers = original_workers
        
        return results
    
    async def _run_warmup(
        self,
        file_processor,
        warmup_files: List[Path],
        worker_count: int
    ) -> None:
        """Run warmup to stabilize performance.
        
        Args:
            file_processor: File processor instance
            warmup_files: Files to use for warmup
            worker_count: Number of workers
        """
        print(f"Running warmup with {len(warmup_files)} files...")
        
        metrics = ThreadSafeMetrics()
        file_processor.num_workers = worker_count
        file_processor.thread_safe_metrics = metrics
        
        await file_processor.initialize_worker_pool()
        
        start_time = time.time()
        for idx, path in enumerate(warmup_files):
            await file_processor.process_file(
                path, idx + 1, len(warmup_files), start_time
            )
        
        await file_processor.shutdown_worker_pool()
    
    def _average_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average multiple metric snapshots.
        
        Args:
            metrics_list: List of metric snapshots
            
        Returns:
            Averaged metrics
        """
        if not metrics_list:
            return {}
        
        # Initialize sums
        sums = {
            'changed': 0,
            'unchanged': 0,
            'errors': 0,
            'total_processed': 0,
            'pattern_time': 0.0,
            'io_time': 0.0,
            'queue_wait_time': 0.0,
        }
        
        # Sum all metrics
        for metrics in metrics_list:
            for key in sums:
                sums[key] += metrics.get(key, 0)
        
        # Calculate averages
        count = len(metrics_list)
        return {k: v / count for k, v in sums.items()}
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def find_optimal_worker_count(
        self,
        results: Dict[int, BenchmarkResult]
    ) -> Tuple[int, BenchmarkResult]:
        """Find the optimal worker count from results.
        
        Args:
            results: Benchmark results by worker count
            
        Returns:
            Tuple of (optimal_count, result)
        """
        if not results:
            raise ValueError("No results to analyze")
        
        # Find configuration with best throughput
        optimal = max(
            results.items(),
            key=lambda x: x[1].files_per_second
        )
        
        return optimal
    
    def generate_report(
        self,
        results: Dict[int, BenchmarkResult]
    ) -> str:
        """Generate a performance report.
        
        Args:
            results: Benchmark results
            
        Returns:
            Formatted report
        """
        if not results:
            return "No benchmark results available"
        
        optimal_count, optimal_result = self.find_optimal_worker_count(results)
        
        report = ["=" * 80]
        report.append("Performance Benchmark Results")
        report.append("=" * 80)
        report.append(f"CPU Count: {self.cpu_count}")
        report.append(f"Total Files: {list(results.values())[0].total_files}")
        report.append("")
        report.append("Results by Worker Count:")
        report.append("-" * 80)
        
        # Sort by worker count
        for count in sorted(results.keys()):
            result = results[count]
            marker = " <-- OPTIMAL" if count == optimal_count else ""
            report.append(f"{result}{marker}")
        
        report.append("-" * 80)
        report.append("")
        report.append(f"Optimal Configuration: {optimal_count} workers")
        report.append(f"Best Performance: {optimal_result.files_per_second:.1f} files/second")
        
        # Calculate speedup over single worker
        if 1 in results:
            speedup = optimal_result.files_per_second / results[1].files_per_second
            report.append(f"Speedup vs 1 worker: {speedup:.2f}x")
        
        report.append("=" * 80)
        
        return "\n".join(report)