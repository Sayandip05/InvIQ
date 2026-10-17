# 🏎️ InvIQ Benchmark & Performance Profiling Suite

This directory contains dedicated performance benchmarking, latency profiling, and load testing tools for the InvIQ intelligent inventory platform.

---

## 📁 Directory Structure

- **`run_latency_benchmark.py`**: Executes real local/cloud latency profiling across:
  1. **Critical API Endpoints**: Synthetic concurrent load testing producing **p50**, **p95**, and **p99** percentiles.
  2. **AI RAG Pipeline**: Vector retrieval + LLM inference round-trip timing.
  3. **WebSocket Push Latency**: Server-to-client alert delivery delta timing.
  4. **Database Query Profiler**: Real SQLAlchemy query execution profiling.
- **`locustfile.py`**: Distributed load testing suite with Locust simulating concurrent pharmacy users.
- **`benchmark_results.json`**: Automated output containing measured percentiles (p50, p95, p99), averages, min/max, and query timings.

**Measured result (committed `benchmark_results.json`):** the assistant path (`ai.total_rag`) averaged **4,950 ms** on the Aug 17 run and **2,460 ms** on the Aug 25 run — both under 5 s. The `llm_inference` stage reads **0** because those runs had no Groq key, so the rule-based fallback answered; the total still measures the full assistant path.

---

## 📊 Latency Percentiles Explained

| Metric | Description | Target SLA |
|---|---|---|
| **p50 (Median)** | 50% of requests complete faster than this time | `< 10ms` (cached) / `< 30ms` (DB) |
| **p95 (95th Percentile)** | 95% of requests complete faster than this time | `< 50ms` (cached) / `< 150ms` (DB) |
| **p99 (Tail Latency)** | 99% of requests complete faster than this time | `< 250ms` |
| **AI RAG p50** | Vector retrieval + Groq LLM inference round-trip | `< 2000ms` |
| **WebSocket p50** | Real-time critical stock alert push latency | `< 100ms` |

---

## 🚀 How to Run

### 1. Run Real Latency & Profiling Benchmark:
```bash
python backend/tests/benchmark/run_latency_benchmark.py
```
*Outputs real p50, p95, p99 percentiles directly into `backend/tests/benchmark/benchmark_results.json`.*

### 2. Run Locust Load Testing:
```bash
locust -f backend/tests/benchmark/locustfile.py --host=http://localhost:8000
```
Open [http://localhost:8089](http://localhost:8089) in your browser to start generating concurrent virtual user traffic.
