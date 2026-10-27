# SecureVision AI — Machine Learning Implementation Audit

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Auditor / Specialist:** Senior Machine Learning & MLOps Audit Team  
**Scope:** Model Architecture, Hyperparameter Verification, Preprocessing Integrity, and Production Safety

---

## 1. Audit Scope & Component Mapping

An exhaustive codebase inspection of SecureVision AI was conducted across the following primary files:

| Component | File Path | Role | Verified Implementation |
|---|---|---|---|
| **Training Pipeline** | `scripts/train_model.py` | Production training & artifact generation | Loads CSV, fits `StandardScaler`, trains `IsolationForest`, saves artifacts to `models/` |
| **Evaluation Pipeline** | `scripts/evaluate_model.py` | Standalone CLI evaluation | Calls `run_evaluation_pipeline()`, outputs metrics without touching `models/` |
| **Evaluation Service** | `backend/services/evaluation.py` | Core evaluation logic | Chronological splitting, isolated in-memory training, full metric calculation |
| **Anomaly Detector** | `backend/services/detector.py` | Production & in-memory inference | `IsolationForestAnomalyDetector`, supports `save_artifacts=False` |
| **Preprocessing** | `backend/services/preprocessing.py` | Feature extraction & scaling | `StandardScaler`, supports `save_artifact=False` |
| **Log Parser** | `backend/services/parser.py` | Network CSV parser | Normalizes headers, validates 19 numerical features |
| **REST API Engine** | `backend/routes/api.py` | Prediction & scan endpoints | Validates models, prevents silent auto-training, returns HTTP 503 on missing artifacts |
| **Automated Tests** | `backend/tests/test_api.py` | Pytest verification suite | 47 automated tests covering APIs, ML, artifact integrity, and explanations |

---

## 2. Estimator Architecture & Hyperparameter Verification

### 2.1 Active Estimator
- **Class:** `sklearn.ensemble.IsolationForest`
- **Reference Code:** `backend/services/detector.py` (Lines 37-47)
- **Production Artifact:** `models/isolation_forest.joblib` (1,235,640 bytes)

### 2.2 Verified Hyperparameters
Inspection of `backend/services/detector.py` and `models/model_metadata.json` confirms the active hyperparameter configuration:
- `n_estimators`: `100` (Number of isolation trees in the ensemble)
- `contamination`: `0.10` (Decision threshold parameter calibrated via validation data)
- `random_state`: `42` (Enforces deterministic tree construction and split reproducibility)
- `n_jobs`: `-1` (Utilizes all available CPU cores for parallelized tree generation)
- `max_samples`: `"auto"` (Defaults to $\min(256, n)$, preventing tree saturation)
- `max_features`: `1.0` (All 19 flow features evaluated per tree)
- `bootstrap`: `False` (Samples drawn without replacement)
- `warm_start`: `False` (Fresh model constructed on each fit)

---

## 3. Preprocessing, Feature Space, & Scaler Resolution

### 3.1 Documentation vs Code Discrepancy Resolution
- **Defect Discovered:** Legacy `README.md` and `PROJECT_REPORT.md` stated that the pipeline employed `RobustScaler`.
- **Code Inspection:** `backend/services/preprocessing.py` explicitly instantiates:
  ```python
  from sklearn.preprocessing import StandardScaler
  scaler = StandardScaler()
  ```
- **Remediation:** In accordance with the remediation directive, we did **not** change the scaler algorithm solely to match stale documentation. Instead, all architectural documentation, viva voce notes, and project reports have been corrected to reflect `StandardScaler`.
- **Production Artifact:** `models/scaler.joblib` (1,791 bytes) stores a fitted `StandardScaler` with mean and scale vectors for 19 features.

### 3.2 Canonical 19-Feature Input Space
The system strictly enforces an invariant feature schema across training, evaluation, and inference:
1. `flow_duration`
2. `total_fwd_packets`
3. `total_bwd_packets`
4. `total_length_of_fwd_packets`
5. `total_length_of_bwd_packets`
6. `fwd_packet_length_mean`
7. `bwd_packet_length_mean`
8. `flow_bytes_per_s`
9. `flow_packets_per_s`
10. `fwd_iat_mean`
11. `bwd_iat_mean`
12. `flow_iat_mean`
13. `active_mean`
14. `idle_mean`
15. `syn_flag_count`
16. `ack_flag_count`
17. `psh_flag_count`
18. `rst_flag_count`
19. `fin_flag_count`

### 3.3 Data Sanitation & Missing Value Policy
In `backend/services/preprocessing.py`:
- Missing feature values are imputed with median values derived strictly from the training dataset.
- Infinite values (`np.inf`, `-np.inf`) are clipped to the 99.9th percentile to prevent numerical overflow in the scaler.
- Categorical identifiers (`source_ip`, `destination_ip`, `protocol`, `timestamp`) and ground-truth `label` columns are strictly dropped before transformation.

---

## 4. End-to-End Prediction Lifecycle

Tracing a single uploaded flow record through the inference pipeline:

1. **Ingestion & Validation (`backend/services/parser.py`):**
   - The CSV file is streamed and validated. Headers are sanitized to lowercase snake_case.
   - The parser asserts the presence of the 19 required features; missing columns raise HTTP 422.
2. **Feature Extraction & Scaling (`backend/services/preprocessing.py`):**
   - Features are extracted in canonical order.
   - The pre-fitted `models/scaler.joblib` transforms raw inputs: $z = (x - \mu) / \sigma$.
3. **Inference & Prediction Conversion (`backend/services/detector.py`):**
   - Native `IsolationForest.predict(X_scaled)` produces $-1$ (outlier) or $+1$ (inlier).
   - The detector maps:
     - Native $-1 \to \text{Application Class } 1$ (**Anomalous**)
     - Native $+1 \to \text{Application Class } 0$ (**Normal**)
   - `decision_function(X_scaled)` produces an anomaly score. Application anomaly scores are normalized to a 0.0–1.0 index for security operators.
4. **Severity Classification:**
   - Score $\ge 0.70$: `CRITICAL`
   - Score $\ge 0.50$: `HIGH`
   - Score $\ge 0.30$: `MEDIUM`
   - Score $< 0.30$: `LOW` (or `NORMAL` if unflagged)
5. **Statistical Explanation Generation (`backend/services/detector.py`):**
   - The engine computes feature z-scores against training metadata (`models/feature_metadata.json`).
   - Features exceeding $|z| \ge 2.0$ or falling outside 1.5×IQR are surfaced as key contributors.
   - Explanations are strictly framed as statistical anomalies rather than causal proof of malicious attack.
6. **Database Persistence:**
   - Results are committed to the SQLite database under `scans` and `alerts` tables.

---

## 5. Summary of Remediated Defects

1. **Destructive Evaluation Overwriting:**
   - *Previous Defect:* `evaluate_model.py` invoked `det.train()` directly, overwriting `models/isolation_forest.joblib` and `models/scaler.joblib`.
   - *Remediation:* Implemented parameter `save_artifacts=False` in `fit_scaler()` and `train()`. Evaluation now runs completely in-memory, leaving production model hashes identical before and after benchmarking.
2. **Silent Retraining on Missing Model:**
   - *Previous Defect:* `backend/routes/api.py` attempted to silently retrain a model from dummy data if artifacts were missing during a user scan request.
   - *Remediation:* Replaced with an explicit HTTP 503 error instructing the administrator to run `scripts/train_model.py`.
3. **Random vs Chronological Splitting:**
   - *Previous Defect:* Evaluation used random splitting, introducing cross-session look-ahead leakage.
   - *Remediation:* Transitioned to chronological holdout splitting (70% train / 15% validation / 15% test).
4. **Documentation Scaler Mismatch:**
   - *Previous Defect:* Discrepancy between code (`StandardScaler`) and docs (`RobustScaler`).
   - *Remediation:* Updated all documentation to accurately describe `StandardScaler`.
