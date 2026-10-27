# SecureVision AI — Test Execution & Regression Report

**Execution Date:** October 25, 2026  
**Platform:** Windows 11 Enterprise, CPython 3.11.13  
**Test Framework:** Pytest 7.4.3 with AnyIO 3.7.1 plugin  
**Working Directory:** `N:\rohit project\log analyzer`  

---

## 1. Test Suite Summary

- **Total Test Cases Collected:** 52
- **Passed:** 52 (100%)
- **Failed:** 0
- **Skipped / Errored:** 0
- **Execution Time:** ~6.1 seconds
- **Test Command:**
  ```powershell
  .\venv\Scripts\python -m pytest backend/tests/test_api.py -v
  ```

---

## 2. Granular Results by Test Class

| Test Class | Method Name | Status | Description |
|---|---|:---:|---|
| `TestHealthEndpoint` | `test_health_check` | **PASSED** | Verifies database connectivity and model status on `/health`. |
| `TestDashboardSummary` | `test_summary_returns_data` | **PASSED** | Validates aggregate scan totals, anomaly rate, and severity distribution. |
| `TestCSVParser` | `test_parse_valid_csv` | **PASSED** | Validates 40-row valid CSV ingestion and header normalization. |
| `TestCSVParser` | `test_parse_empty_file` | **PASSED** | Ensures 0-byte file upload raises `ParseError`. |
| `TestCSVParser` | `test_parse_headers_only` | **PASSED** | Ensures headers without data rows trigger validation error. |
| `TestCSVParser` | `test_parse_insufficient_features` | **PASSED** | Rejects CSV files having fewer than 3 supported features. |
| `TestCSVParser` | `test_column_normalization` | **PASSED** | Maps diverse variations (`Flow Duration`, ` Label`) to canonical keys. |
| `TestCSVParser` | `test_file_size_limit` | **PASSED** | Enforces upload byte constraints. |
| `TestUploadEndpoint` | `test_upload_valid_csv` | **PASSED** | Full POST `/api/v1/scans` flow with analysis persistence. |
| `TestUploadEndpoint` | `test_upload_empty_file` | **PASSED** | Returns HTTP 422 on empty file payload. |
| `TestUploadEndpoint` | `test_upload_non_csv` | **PASSED** | Rejects non-CSV extensions. |
| `TestUploadEndpoint` | `test_upload_insufficient_features` | **PASSED** | Returns HTTP 422 when features are insufficient. |
| `TestScanEndpoints` | `test_list_scans` | **PASSED** | Paginated scan listing returns correct schema. |
| `TestScanEndpoints` | `test_list_scans_pagination` | **PASSED** | Page navigation constraints and boundaries. |
| `TestScanEndpoints` | `test_get_scan_not_found` | **PASSED** | Returns HTTP 404 for invalid scan ID. |
| `TestAlertEndpoints` | `test_list_alerts` | **PASSED** | Lists alert records associated with completed scans. |
| `TestAlertEndpoints` | `test_filter_alerts_by_prediction` | **PASSED** | Filters alerts by binary prediction (`prediction=1`). |
| `TestAlertEndpoints` | `test_filter_alerts_by_severity` | **PASSED** | Filters alerts by severity category (`critical`, `high`, etc.). |
| `TestAlertEndpoints` | `test_alert_not_found` | **PASSED** | Returns HTTP 404 for missing alert ID. |
| `TestAlertEndpoints` | `test_export_alerts` | **PASSED** | Validates downloadable CSV export stream. |
| `TestAlertEndpoints` | `test_export_filtered_alerts` | **PASSED** | Exports only filtered subset of alerts. |
| `TestModelEndpoint` | `test_model_status` | **PASSED** | Returns model status, hyperparameters, and feature list. |
| `TestResearchEndpoint` | `test_research_metrics` | **PASSED** | Retrieves recorded benchmark evaluation results from database. |
| `TestMLPipeline` | `test_preprocessing_pipeline` | **PASSED** | Tests feature selection, median imputation, and standard scaling. |
| `TestMLPipeline` | `test_detector_predict` | **PASSED** | Verifies predictions and anomaly scores vector lengths. |
| `TestMLPipeline` | `test_severity_classification` | **PASSED** | Validates score-to-severity mapping boundaries. |
| `TestMLPipeline` | `test_evaluation_metrics` | **PASSED** | Verifies precision, recall, F1, and confusion matrix calculation. |
| `TestMLPipeline` | `test_label_conversion` | **PASSED** | Maps string labels (`BENIGN` vs attacks) to binary {0, 1}. |
| `TestExplanations` | `test_generate_explanation_anomalous` | **PASSED** | Generates feature attribution for anomalous flows. |
| `TestExplanations` | `test_generate_explanation_normal` | **PASSED** | Produces normal baseline summary for inlier flows. |
| `TestExplanations` | `test_investigation_steps` | **PASSED** | Generates prioritized SOC playbook steps with context. |
| `TestDatabasePersistence` | `test_scan_persists_after_upload` | **PASSED** | Verifies database durability of scan metadata. |
| `TestDatabasePersistence` | `test_alerts_persist_after_upload` | **PASSED** | Verifies individual alert records persist correctly. |
| `TestErrorHandling` | `test_invalid_page_parameter` | **PASSED** | Rejects negative pagination indexes with HTTP 422. |
| `TestErrorHandling` | `test_invalid_prediction_filter` | **PASSED** | Rejects invalid prediction values (e.g. `prediction=5`). |
| `TestErrorHandling` | `test_scan_not_found` | **PASSED** | 404 handling for scan ID 0. |
| `TestErrorHandling` | `test_alert_not_found` | **PASSED** | 404 handling for alert ID 0. |
| `TestPredictionSchema` | `test_predictions_are_binary` | **PASSED** | Validates that all prediction outputs strictly adhere to {0, 1}. |
| `TestArtifactProtectionAndEvaluationIntegrity` | `test_evaluation_pipeline_does_not_modify_production_artifacts` | **PASSED** | **Regression test**: Computes SHA-256 of all artifacts in `models/` before and after `run_evaluation_pipeline()`, asserting 100% hash identity. |
| `TestArtifactProtectionAndEvaluationIntegrity` | `test_fit_scaler_does_not_overwrite_by_default` | **PASSED** | **Regression test**: Verifies in-memory `preprocess_pipeline(fit=True)` does not touch `models/scaler.joblib`. |
| `TestArtifactProtectionAndEvaluationIntegrity` | `test_detector_train_in_memory_mode` | **PASSED** | **Regression test**: Verifies `AnomalyDetector.train(save_artifacts=False)` trains without writing to disk. |
| `TestArtifactProtectionAndEvaluationIntegrity` | `test_chronological_holdout_protocol` | **PASSED** | **Regression test**: Confirms temporal log sorting partitions sequentially without label leakage into features. |
| `TestEvaluationMetricsCalculation` | `test_mathematical_metric_accuracy_deterministic_fixture` | **PASSED** | **Regression test**: Validates mathematical formulas for Accuracy, Precision, Recall, Specificity, FPR, and FNR against hand-computed ground truth. |
| `TestEvaluationMetricsCalculation` | `test_zero_denominator_safe_handling` | **PASSED** | **Regression test**: Ensures edge cases with 0 true or predicted positives do not crash with `ZeroDivisionError`. |
| `TestEvaluationMetricsCalculation` | `test_positive_class_convention_is_anomaly` | **PASSED** | **Regression test**: Asserts positive class $y=1$ is strictly bound to attack/anomalous traffic. |
| `TestExplanationTransparencyAndRobustness` | `test_constant_feature_zero_std_no_crash` | **PASSED** | **Regression test**: Asserts zero variance features ($\sigma=0$) do not cause division by zero during $z$-score calculation. |
| `TestExplanationTransparencyAndRobustness` | `test_explanations_do_not_claim_causal_proof` | **PASSED** | **Regression test**: Enforces statistical framing ("statistical deviation") and forbids unsubstantiated causal claims. |
| `TestSecurityAndRobustness` | `test_invalid_sort_by_defaults_safely` | **PASSED** | **Security test**: Verifies non-column query values (`?sort_by=__table__`) default safely rather than raising 500 errors. |
| `TestSecurityAndRobustness` | `test_sql_injection_attempt_in_search_parameter` | **PASSED** | **Security test**: Verifies SQL injection payloads are properly escaped by SQLAlchemy ORM. |
| `TestSecurityAndRobustness` | `test_csv_formula_injection_defense` | **PASSED** | **Security test**: Verifies cells with `=`, `+`, `-`, `@` are prepended with `'` in exported CSVs. |
| `TestSecurityAndRobustness` | `test_unsupported_encoding_handled_safely` | **PASSED** | **Security test**: Verifies corrupted binary payloads return clean 422 errors without stack trace exposure. |
| `TestSecurityAndRobustness` | `test_file_size_limit_enforced` | **PASSED** | **Security test**: Enforces 50 MB file upload ceiling. |

---

## 3. Production Artifact Integrity Audit

Cryptographic SHA-256 hashes of all four production artifacts in `models/` were verified before and after all test suites and evaluation runs:

| File | File Size | Baseline SHA-256 | Final SHA-256 | Status |
|---|:---:|---|---|:---:|
| `models/isolation_forest.joblib` | 1,235,640 bytes | `ba824e863dc68a291c5904c4655da24abc06262b0ab742aa02c921653d71fcdf` | `BA824E863DC68A291C5904C4655DA24ABC06262B0AB742AA02C921653D71FCDF` | **Unchanged** |
| `models/scaler.joblib` | 1,791 bytes | `bf7e2067327b6d306fb0760f64abd27153267342f300d2db37232087c7fa10e7` | `BF7E2067327B6D306FB0760F64ABD27153267342F300D2DB37232087C7FA10E7` | **Unchanged** |
| `models/model_metadata.json` | 777 bytes | `7e529f47042daa6c7d41a6f705c1e40b3aa15cf09ec0e0eb9f31cd4bb37bc8b1` | `7E529F47042DAA6C7D41A6F705C1E40B3AA15CF09EC0E0EB9F31CD4BB37BC8B1` | **Unchanged** |
| `models/feature_metadata.json` | 3,920 bytes | `cebcce957c0d7d836f887dd281d916bda4c1702251d59e05ed7c7b81595e0919` | `CEBCCE957C0D7D836F887DD281D916BDA4C1702251D59E05ED7C7B81595E0919` | **Unchanged** |

---

## 4. Evaluation Benchmark Metrics (Held-Out Test Partition)

- **Dataset:** `data/benchmark_50k.csv` (50,000 network flows)
- **Split Method:** Chronological holdout (35,000 train / 7,500 val / 7,500 test)
- **Held-Out Test Records:** 7,500 flows
- **Ground-Truth Distribution:** Normal = 6,363 flows (84.84%), Anomalous = 1,137 flows (15.16%)
- **Model Flagged Anomalies:** 753 flows (10.04% predicted anomaly rate)
- **Measured Metrics:**
  - **Accuracy:** `92.59%` (0.9259)
  - **Precision:** `88.58%` (0.8858)
  - **Recall (Detection Rate):** `58.66%` (0.5866)
  - **F1-Score:** `70.58%` (0.7058)
  - **Specificity:** `98.65%` (0.9865)
  - **False Positive Rate:** `1.35%` (0.0135)
  - **False Negative Rate:** `41.34%` (0.4134)
  - **Confusion Matrix:** TN = 6,277, FP = 86, FN = 470, TP = 667
