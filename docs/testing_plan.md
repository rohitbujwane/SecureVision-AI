# SecureVision AI — Master Testing Plan

**Document Version:** 1.0.0  
**Effective Date:** October 25, 2026  
**Lead QA Engineer / Security Specialist:** Senior QA, Performance & ML Validation Team  
**Scope:** Functional Verification, Security Assessment, API Contracts, Machine Learning Evaluation, and Performance Profiling

---

## 1. Objectives & Scope

The purpose of this testing plan is to establish a rigorous, repeatable QA methodology for SecureVision AI. Testing covers:
1. **Component Testing:** Parser, Preprocessing, Detector, Explanations, Database Persistence.
2. **API Contract Verification:** All 12 implemented endpoints, error states, and schema compliance.
3. **Security Testing:** Input sanitization, SQL injection defense, CSV formula injection defense, path traversal prevention, file size boundaries, and error message sanitization.
4. **Machine Learning Evaluation:** Non-destructive evaluation on a chronological holdout partition, complete metric suite (Accuracy, Precision, Recall, F1, Specificity, FPR, FNR), baseline comparisons, and artifact hash invariance.
5. **Frontend Workflow Testing:** End-to-end browser verification of the dashboard, drag-and-drop file ingestion, alerts table, and model telemetry.
6. **Performance & Stress Testing:** Startup profiling, latency (p50, p95, p99), throughput (RPS), memory leak detection, concurrent requests, and batch scalability.

---

## 2. Test Environment & Software Stack

- **Operating System:** Windows 11 Enterprise (64-bit)
- **Runtime:** Python 3.11.13 Virtual Environment (`.\venv\`)
- **Web Framework:** FastAPI 0.104.1 + Uvicorn 0.24.0 (ASGI)
- **Database Engine:** SQLite 3 (SQLAlchemy ORM)
- **Machine Learning Core:** Scikit-Learn 1.3.2 (`IsolationForest`, `StandardScaler`), NumPy 1.26.2, Pandas 2.1.3, Joblib 1.3.2
- **Testing Framework:** Pytest 7.4.3 + AnyIO 3.7.1 + HTTPX 0.25.2
- **Browser Automation:** Antigravity Browser Agent (Chromium headless engine)

---

## 3. Test Categories & Traceability Matrix

| Test Suite ID | Component / Module | Scope & Objectives | Test Count |
|---|---|---|:---:|
| `TC-HLTH` | Health & Readiness | Verifies `/health` endpoint and database connectivity. | 1 |
| `TC-DASH` | Dashboard Summary | Verifies `/api/v1/summary` metric cards and chart aggregations. | 1 |
| `TC-PARS` | CSV Parser | Tests valid files, empty files, headers-only, insufficient features, and column normalization. | 6 |
| `TC-UPLD` | Scan Uploads | Tests valid uploads, empty files, non-CSV files, and insufficient feature handling. | 4 |
| `TC-SCAN` | Scan Management | Tests scan retrieval, pagination, and 404 error states. | 3 |
| `TC-ALRT` | Alert Management | Tests alert filtering by prediction, severity, export to CSV, and 404 error states. | 6 |
| `TC-MODL` | Model Status | Tests `/api/v1/model/status` response schema and metadata. | 1 |
| `TC-RSCH` | Research Metrics | Tests `/api/v1/research/metrics` experiment history retrieval. | 1 |
| `TC-MLPL` | ML Pipeline | Tests preprocessing scaling, detector inference, severity grading, metrics calculation, and label mapping. | 5 |
| `TC-EXPL` | Explanations | Tests z-score explanations, normal vs anomalous logic, and investigation steps. | 3 |
| `TC-PERS` | Persistence | Verifies SQLite commit of scans and alerts. | 2 |
| `TC-ERRS` | Error Handling | Tests boundary conditions on query parameters and invalid filters. | 4 |
| `TC-SCHM` | Prediction Schema | Asserts binary prediction values ($0 \in \text{Normal}, 1 \in \text{Anomaly}$). | 1 |
| `TC-PROT` | Artifact Protection | Asserts evaluation pipeline does not modify production artifact SHA-256 hashes. | 4 |
| `TC-MTRC` | Evaluation Metrics | Asserts mathematical accuracy of Accuracy, Precision, Recall, Specificity, FPR, and FNR. | 3 |
| `TC-SAFE` | Explanation Transparency | Verifies constant feature std=0 safety and absence of unverified causal claims. | 2 |
| `TC-SECR` | Security & Robustness | Tests sort_by attribute whitelist, SQL injection resistance, CSV formula injection defense, and encoding safety. | 5 |
| **TOTAL** | **Automated Suite** | **Comprehensive pytest suite ([backend/tests/test_api.py](file:///n:/rohit%20project/log%20analyzer/backend/tests/test_api.py))** | **52** |

---

## 4. Performance & Stress Testing Matrix

| Benchmark ID | Test Description | Target Workload | Key Metrics Measured |
|---|---|---|---|
| `PERF-01` | Server & Model Startup | Cold process restart | Model load time (ms), metadata load time (ms) |
| `PERF-02` | Core Endpoint Latency | `/health`, `/api/v1/summary`, `/api/v1/alerts` | Avg, p50, p95, p99 latency (ms), RPS |
| `PERF-03` | Pipeline Breakdown | 10,000 network flows | Parsing (ms), Scaling (ms), Tree inference (ms), $\mu$s/row |
| `PERF-04` | Batch Scalability | 100, 1,000, 5,000, 10,000 rows | Latency (ms), Throughput (rows/s), Error rate (%) |
| `PERF-05` | Memory Stability | 15 iterations of 1,000 flows | Initial, final, peak memory (MB), growth detection |
| `PERF-06` | Concurrency & Stress | 5 concurrent workers, 15 requests | p50 latency (ms), concurrency RPS, error rate (%) |

---

## 5. Security & Defensive Boundaries

1. **Input Injection:** All database operations utilize SQLAlchemy parameterized ORM queries; verified immune to SQL injection.
2. **Path Traversal:** File endpoints (`/api/v1/report`, `/api/v1/report/download`) strictly reference static paths within `BASE_DIR`; arbitrary directory traversal is impossible.
3. **CSV Formula Injection:** User-supplied strings in CSV alert export starting with `=`, `+`, `-`, or `@` are neutralized by prepending `'`.
4. **File Upload Restrictions:** Maximum file size enforced at 50 MB; non-CSV files rejected with HTTP 400; malformed files rejected with HTTP 422.
5. **Error Sanitization:** Internal stack traces and server file paths are withheld from client responses; errors return structured JSON details.
