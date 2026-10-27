# SecureVision AI — Model Evaluation Protocol

**Document Version:** 1.0.0  
**Effective Date:** October 25, 2026  
**Auditor / Specialist:** Senior Machine Learning & MLOps Audit Team  
**Scope:** Standalone Benchmarking, Temporal Holdout Rules, Session Leakage Prevention, and Artifact Isolation

---

## 1. Objectives & Guiding Principles

The SecureVision AI Evaluation Protocol defines the mandatory standards for assessing anomaly detection performance. To ensure academic rigor and operational safety, any benchmark must adhere to four core principles:

1. **Production Isolation:** Under no circumstances may an evaluation command overwrite, alter, or retrain the production model or scaler artifacts located in `models/`.
2. **Leak-Free Partitioning:** The held-out test partition must remain strictly untouched during preprocessing parameter calculation, model fitting, and contamination tuning.
3. **Chronological Splitting:** Where timestamps exist, data must be partitioned chronologically to mirror real-world intrusion detection scenarios.
4. **Comprehensive Metric Reporting:** Models must be assessed using a complete suite of classification metrics and compared against an All-Normal baseline.

---

## 2. Dataset Requirements & Schema

### 2.1 Supported Datasets
The primary benchmark dataset is `data/benchmark_50k.csv` (derived from CIC-IDS2017 flow captures, containing 50,000 network flows).

### 2.2 Canonical Input Schema
Every evaluation dataset must contain:
1. `timestamp`: ISO-8601 string or numeric unix epoch for chronological sorting.
2. The 19 canonical flow features:
   - `flow_duration`, `total_fwd_packets`, `total_bwd_packets`, `total_length_of_fwd_packets`, `total_length_of_bwd_packets`, `fwd_packet_length_mean`, `bwd_packet_length_mean`, `flow_bytes_per_s`, `flow_packets_per_s`, `fwd_iat_mean`, `bwd_iat_mean`, `flow_iat_mean`, `active_mean`, `idle_mean`, `syn_flag_count`, `ack_flag_count`, `psh_flag_count`, `rst_flag_count`, `fin_flag_count`.
3. `label`: Binary ground truth (`0` for benign traffic, `1` for malicious attack flows).

---

## 3. Data Splitting & Leakage Mitigation

### 3.1 Three-Way Chronological Holdout
Data is sorted chronologically and partitioned into three disjoint sets:

```
[===================== TRAIN (70%) =====================] [=== VAL (15%) ===] [=== TEST (15%) ===]
Row 1 ------------------------------------------- Row 35,000 | Row 35,001-42,500 | Row 42,501-50,000
   Used to fit StandardScaler and candidate models         Used for tuning     Frozen benchmark
```

- **Training Partition (70.0% / 35,000 rows):** Used to fit `StandardScaler` ($\mu, \sigma$) and train candidate `IsolationForest` instances.
- **Validation Partition (15.0% / 7,500 rows):** Used to compare contamination factors ($c \in \{0.05, 0.08, 0.10, 0.15\}$) and decision offsets.
- **Test Partition (15.0% / 7,500 rows):** Evaluated exactly once using the frozen model and frozen threshold.

### 3.2 Leakage Rules
- **No Test Preprocessing:** `StandardScaler` is fitted solely on `df_train`. `df_val` and `df_test` are transformed using `scaler.transform()`.
- **Target Exclusion:** The `label` column is strictly removed prior to scaling and model ingestion.
- **Session Analysis:** Evaluation scripts track IP session overlap between training and test sets to detect multi-stage attack persistence.

---

## 4. Metric Calculations & Standards

All metrics are calculated using `backend/services/evaluation.py`:

1. **Overall Accuracy:** $\frac{TP + TN}{TP + TN + FP + FN}$
2. **Precision:** $\frac{TP}{TP + FP}$
3. **Recall (Detection Rate):** $\frac{TP}{TP + FN}$
4. **F1-Score:** $2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$
5. **Specificity:** $\frac{TN}{TN + FP}$
6. **False Positive Rate (FPR):** $\frac{FP}{FP + TN}$
7. **False Negative Rate (FNR):** $\frac{FN}{FN + TP}$
8. **Anomaly Prevalence:** $\frac{TP + FN}{\text{Total}}$
9. **Predicted Anomaly Rate:** $\frac{TP + FP}{\text{Total}}$

### Baseline Requirement:
Every evaluation report must include the **All-Normal Baseline** ($y=0$ for all flows) to expose the accuracy paradox inherent in imbalanced security data.

---

## 5. Artifact Protection Architecture

To guarantee production safety:
1. `backend/services/preprocessing.py`:
   - `fit_scaler(df, save_artifact=False)` creates and fits an in-memory `StandardScaler`.
   - Artifact saving is only triggered when explicitly passed `save_artifact=True` during designated production retraining.
2. `backend/services/detector.py`:
   - `train(self, df, ..., save_artifacts=False)` fits the in-memory tree ensemble without calling `.joblib.dump()` on production paths.
3. `scripts/evaluate_model.py`:
   - Output reports are saved strictly to `research/results/evaluation_<timestamp>.json`.
   - Never touches `models/`.

---

## 6. How to Run the Evaluation Protocol

### 6.1 Automated Pytest Regression Check
To verify that evaluation code does not overwrite production artifacts:
```bash
.\venv\Scripts\python.exe -m pytest backend/tests/test_api.py -k "test_evaluation_pipeline_does_not_modify_production_artifacts" -v
```

### 6.2 Standalone Benchmark Command
To execute the complete chronological holdout evaluation pipeline:
```bash
.\venv\Scripts\python.exe scripts/evaluate_model.py --data data/benchmark_50k.csv --split auto --test-size 0.15 --val-size 0.15 --contamination 0.10
```

### 6.3 Verifying Model Hash Invariance
Run the SHA-256 verification command before and after benchmarking:
```powershell
Get-FileHash models/isolation_forest.joblib, models/scaler.joblib, models/model_metadata.json, models/feature_metadata.json -Algorithm SHA256
```
Hashes must remain completely identical.
