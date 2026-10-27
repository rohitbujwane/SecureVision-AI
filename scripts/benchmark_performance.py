"""
SecureVision AI — Performance, Stress & Reliability Benchmark Suite.
Measures latency (p50, p95, p99), throughput (RPS), error rates,
memory usage, and time breakdown across request sizes and concurrency.
"""

import time
import tracemalloc
import json
import io
import sys
import statistics
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
import httpx

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

BASE_URL = "http://127.0.0.1:8000"
DATA_DIR = Path("data")


def measure_startup_and_loading():
    """Measure model loading time and feature metadata loading time."""
    from backend.services.detector import AnomalyDetector
    
    t0 = time.perf_counter()
    detector = AnomalyDetector()
    load_success = detector.load()
    t_load = (time.perf_counter() - t0) * 1000  # ms
    
    t0 = time.perf_counter()
    feature_stats = detector.get_feature_stats()
    t_meta = (time.perf_counter() - t0) * 1000  # ms
    
    return {
        "load_success": load_success,
        "model_loading_ms": round(t_load, 2),
        "feature_meta_loading_ms": round(t_meta, 2),
        "features_loaded": len(detector.features),
        "version": detector.version,
    }


def benchmark_endpoint(url: str, n_requests: int = 50) -> Dict[str, Any]:
    """Measure latency and throughput for a GET endpoint."""
    latencies = []
    errors = 0
    client = httpx.Client(timeout=30.0)
    
    # Warmup
    try:
        client.get(url)
    except Exception:
        pass

    t_start = time.perf_counter()
    for _ in range(n_requests):
        t0 = time.perf_counter()
        try:
            res = client.get(url)
            if res.status_code == 200:
                latencies.append((time.perf_counter() - t0) * 1000)
            else:
                errors += 1
        except Exception:
            errors += 1
    total_time = time.perf_counter() - t_start
    client.close()

    if not latencies:
        return {"error": "All requests failed"}

    latencies.sort()
    rps = n_requests / total_time
    return {
        "url": url,
        "n_requests": n_requests,
        "avg_ms": round(statistics.mean(latencies), 2),
        "median_p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2),
        "p99_ms": round(latencies[int(len(latencies) * 0.99)], 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "rps": round(rps, 2),
        "error_rate_pct": round((errors / n_requests) * 100, 2),
    }


def benchmark_inference_breakdown(df_sample: pd.DataFrame) -> Dict[str, Any]:
    """Measure precise breakdown of parsing, preprocessing, model inference, and explanation."""
    from backend.services.parser import parse_csv
    from backend.services.preprocessing import preprocess_pipeline
    from backend.services.detector import detector
    from backend.services.explanations import generate_explanation

    # Prepare CSV content in memory
    buf = io.StringIO()
    df_sample.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    # Ensure detector singleton is loaded
    if not detector.is_trained:
        detector.load()

    # 1. Parsing
    t0 = time.perf_counter()
    df_parsed, parse_info = parse_csv(csv_bytes)
    t_parse = (time.perf_counter() - t0) * 1000

    # 2. Preprocessing
    t0 = time.perf_counter()
    scaled_data, used_features, _, cleaned_df = preprocess_pipeline(
        df_parsed, feature_list=detector.features, scaler=detector.scaler, fit=False
    )
    t_preprocess = (time.perf_counter() - t0) * 1000

    # 3. Model Inference
    t0 = time.perf_counter()
    raw_preds = detector.model.predict(scaled_data)
    scores = detector.model.decision_function(scaled_data)
    preds = np.where(raw_preds == -1, 1, 0)
    t_infer = (time.perf_counter() - t0) * 1000

    # 4. Explanation generation sample (first 100 rows)
    feature_stats = detector.get_feature_stats()
    t0 = time.perf_counter()
    sample_size = min(100, len(preds))
    for i in range(sample_size):
        feat_vals = {f: float(cleaned_df.iloc[i][f]) for f in used_features if f in cleaned_df.columns}
        generate_explanation(feat_vals, float(scores[i]), "high", feature_stats, int(preds[i]))
    t_explain_100 = (time.perf_counter() - t0) * 1000

    return {
        "rows": len(df_sample),
        "parse_ms": round(t_parse, 2),
        "preprocess_ms": round(t_preprocess, 2),
        "inference_ms": round(t_infer, 2),
        "inference_per_row_us": round((t_infer / len(df_sample)) * 1000, 2),
        "explanation_100_rows_ms": round(t_explain_100, 2),
    }


def benchmark_upload_batch_sizes(data_file: Path) -> List[Dict[str, Any]]:
    """Test uploads across increasing batch sizes (100, 1000, 5000, 10000 rows)."""
    df = pd.read_csv(data_file)
    batch_sizes = [100, 1000, 5000, 10000]
    results = []
    client = httpx.Client(timeout=60.0)

    for size in batch_sizes:
        if size > len(df):
            continue
        sub_df = df.head(size)
        buf = io.StringIO()
        sub_df.to_csv(buf, index=False)
        content = buf.getvalue().encode("utf-8")

        latencies = []
        errors = 0
        reps = 3 if size >= 5000 else 5

        for _ in range(reps):
            t0 = time.perf_counter()
            try:
                res = client.post(
                    f"{BASE_URL}/api/v1/scans",
                    files={"file": (f"test_batch_{size}.csv", io.BytesIO(content), "text/csv")},
                )
                if res.status_code == 200:
                    latencies.append((time.perf_counter() - t0) * 1000)
                else:
                    errors += 1
            except Exception:
                errors += 1

        if latencies:
            results.append({
                "batch_size": size,
                "reps": reps,
                "avg_latency_ms": round(statistics.mean(latencies), 2),
                "p50_latency_ms": round(statistics.median(latencies), 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "throughput_rows_per_sec": round((size / (statistics.median(latencies) / 1000)), 2),
                "error_rate_pct": round((errors / reps) * 100, 2),
            })
    client.close()
    return results


def test_memory_and_leak_detection(n_iterations: int = 15) -> Dict[str, Any]:
    """Profile memory usage over repeated inference cycles."""
    from backend.services.detector import detector
    if not detector.is_trained:
        detector.load()
    
    # Load 1000 rows
    sample_path = DATA_DIR / "sample_logs.csv"
    if not sample_path.exists():
        sample_path = DATA_DIR / "benchmark_50k.csv"
    df = pd.read_csv(sample_path).head(1000)

    tracemalloc.start()
    baseline_curr, baseline_peak = tracemalloc.get_traced_memory()
    
    memory_snapshots = []
    
    for i in range(n_iterations):
        preds, scores, used = detector.predict(df)
        curr, peak = tracemalloc.get_traced_memory()
        memory_snapshots.append(curr / (1024 * 1024))
    
    final_curr, final_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_growth_mb = memory_snapshots[-1] - memory_snapshots[0]
    return {
        "iterations": n_iterations,
        "rows_per_iteration": len(df),
        "initial_memory_mb": round(baseline_curr / (1024 * 1024), 2),
        "final_memory_mb": round(final_curr / (1024 * 1024), 2),
        "peak_memory_mb": round(final_peak / (1024 * 1024), 2),
        "memory_growth_mb": round(memory_growth_mb, 3),
        "leak_detected": bool(memory_growth_mb > 5.0),  # >5MB growth indicates potential leak
    }


def test_concurrency(concurrency: int = 5, n_requests: int = 15) -> Dict[str, Any]:
    """Measure latency and error rate under concurrent requests."""
    import concurrent.futures

    sample_path = DATA_DIR / "sample_logs.csv"
    if not sample_path.exists():
        sample_path = DATA_DIR / "benchmark_50k.csv"
    content = Path(sample_path).read_bytes()[:15000]  # ~100 rows

    latencies = []
    errors = 0

    def make_request():
        client = httpx.Client(timeout=30.0)
        t0 = time.perf_counter()
        try:
            res = client.post(
                f"{BASE_URL}/api/v1/scans",
                files={"file": ("concurrent_test.csv", io.BytesIO(content), "text/csv")},
            )
            lat = (time.perf_counter() - t0) * 1000
            client.close()
            return res.status_code == 200, lat
        except Exception:
            client.close()
            return False, 0.0

    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(n_requests)]
        for f in concurrent.futures.as_completed(futures):
            ok, lat = f.result()
            if ok:
                latencies.append(lat)
            else:
                errors += 1
    total_time = time.perf_counter() - t_start

    if not latencies:
        return {"error": "All concurrent requests failed"}

    return {
        "concurrency": concurrency,
        "total_requests": n_requests,
        "avg_latency_ms": round(statistics.mean(latencies), 2),
        "median_p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        "throughput_rps": round(n_requests / total_time, 2),
        "error_count": errors,
        "error_rate_pct": round((errors / n_requests) * 100, 2),
    }


def main():
    print("=" * 60)
    print("SECUREVISION AI — PERFORMANCE BENCHMARKING SUITE")
    print("=" * 60)

    print("\n[1/5] Measuring Startup & Model Loading...")
    startup_metrics = measure_startup_and_loading()
    print(f"  Model Loading Time: {startup_metrics['model_loading_ms']} ms")
    print(f"  Feature Metadata Loading Time: {startup_metrics['feature_meta_loading_ms']} ms")
    print(f"  Model Version: {startup_metrics['version']}")

    print("\n[2/5] Benchmarking Core Endpoints Latency & Throughput...")
    health_bench = benchmark_endpoint(f"{BASE_URL}/health", n_requests=40)
    summary_bench = benchmark_endpoint(f"{BASE_URL}/api/v1/summary", n_requests=40)
    alerts_bench = benchmark_endpoint(f"{BASE_URL}/api/v1/alerts?page=1&page_size=20", n_requests=40)
    print(f"  GET /health: Avg={health_bench['avg_ms']}ms, p50={health_bench['median_p50_ms']}ms, p95={health_bench['p95_ms']}ms, RPS={health_bench['rps']}")
    print(f"  GET /api/v1/summary: Avg={summary_bench['avg_ms']}ms, p50={summary_bench['median_p50_ms']}ms, p95={summary_bench['p95_ms']}ms, RPS={summary_bench['rps']}")
    print(f"  GET /api/v1/alerts: Avg={alerts_bench['avg_ms']}ms, p50={alerts_bench['median_p50_ms']}ms, p95={alerts_bench['p95_ms']}ms, RPS={alerts_bench['rps']}")

    print("\n[3/5] Measuring Pipeline Processing Breakdown (10,000 rows)...")
    sample_file = DATA_DIR / "benchmark_50k.csv"
    df_10k = pd.read_csv(sample_file).head(10000)
    breakdown = benchmark_inference_breakdown(df_10k)
    print(f"  Rows: {breakdown['rows']}")
    print(f"  CSV Parsing Time: {breakdown['parse_ms']} ms")
    print(f"  Preprocessing Time: {breakdown['preprocess_ms']} ms")
    print(f"  Model Inference Time: {breakdown['inference_ms']} ms ({breakdown['inference_per_row_us']} us/row)")
    print(f"  Explanation Time (100 rows): {breakdown['explanation_100_rows_ms']} ms")

    print("\n[4/5] Benchmarking Upload Workloads across Batch Sizes...")
    batch_results = benchmark_upload_batch_sizes(sample_file)
    for b in batch_results:
        print(f"  Batch {b['batch_size']:>5} rows: p50={b['p50_latency_ms']:>7.2f} ms | Throughput={b['throughput_rows_per_sec']:>9.2f} rows/s | Errors={b['error_rate_pct']}%")

    print("\n[5/5] Profiling Memory Stability & Concurrency...")
    mem_profile = test_memory_and_leak_detection(n_iterations=15)
    print(f"  Memory Profile (15 iterations of 1000 rows):")
    print(f"    Initial: {mem_profile['initial_memory_mb']} MB, Final: {mem_profile['final_memory_mb']} MB, Peak: {mem_profile['peak_memory_mb']} MB")
    print(f"    Memory Growth: {mem_profile['memory_growth_mb']} MB | Leak Detected: {mem_profile['leak_detected']}")

    concurrency_profile = test_concurrency(concurrency=5, n_requests=15)
    print(f"  Concurrency Profile (5 concurrent workers, 15 requests):")
    print(f"    Avg Latency: {concurrency_profile['avg_latency_ms']} ms, p50: {concurrency_profile['median_p50_ms']} ms, RPS: {concurrency_profile['throughput_rps']}")
    print(f"    Error Rate: {concurrency_profile['error_rate_pct']}%")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "startup": startup_metrics,
        "endpoints": {
            "health": health_bench,
            "summary": summary_bench,
            "alerts": alerts_bench,
        },
        "pipeline_breakdown": breakdown,
        "batch_uploads": batch_results,
        "memory_profile": mem_profile,
        "concurrency_profile": concurrency_profile,
    }

    report_path = Path("research/results/performance_benchmark_latest.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[SUCCESS] Performance benchmark results written to: {report_path}")


if __name__ == "__main__":
    main()
