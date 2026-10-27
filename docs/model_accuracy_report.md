# SecureVision AI — Model Accuracy & Performance Validation Report

**Document Version:** 1.0.0  
**Evaluation Date:** October 25, 2026  
**Auditor / Specialist:** Senior Machine Learning & MLOps Review Team  
**Evaluation Target:** Isolation Forest Anomaly Detector (`sklearn.ensemble.IsolationForest`)

---

## 1. Executive Summary

As part of the master remediation audit for SecureVision AI, this evaluation report provides a rigorous, empirical validation of the Isolation Forest anomaly detection model. Software test pass rates confirm system and API stability, but only an isolated, leak-free evaluation on held-out network traffic can establish model detection capability.

The evaluation was executed with an isolated in-memory pipeline (`backend/services/evaluation.py` and `scripts/evaluate_model.py`) that strictly guarantees:
1. **Production artifact protection:** Production models and scalers in `models/` were never modified or overwritten.
2. **Train-only preprocessing:** All numerical standardization (`StandardScaler`) statistics were computed solely on the training partition and transferred to validation/test sets without target leakage.
3. **Temporal chronological holdout:** Data was sorted chronologically; the final 15% (7,500 rows) of the 50,000-flow dataset was strictly reserved as the frozen test benchmark.
4. **Validation-based thresholding:** Contamination parameter selection ($c=0.10$) was validated on a separate 7,500-flow validation partition prior to test scoring.

---

## 2. Evaluation Dataset & Preprocessing

### 2.1 Dataset Profile
- **Dataset Source:** `data/benchmark_50k.csv` (Derived from CIC-IDS2017 / NetFlow traffic captures).
- **Total Records:** 50,000 flow records.
- **Feature Dimensionality:** 19 continuous network flow features (see Section 2.3).
- **Timestamp Column:** `timestamp` (ISO-8601 formatted, sorted chronologically).
- **Ground-Truth Label:** `label` (Binary: `0` = Benign/Normal, `1` = Malicious/Anomaly).
  - *Note on Label Exclusion:* The ground-truth `label` column is strictly isolated from model training features and preprocessing transformations.

### 2.2 Split Strategy & Data Leakage Assessment
A chronologically ordered 70% / 15% / 15% split was executed:
- **Training Partition:** Rows 1 to 35,000 (70.0%) — used solely to fit `StandardScaler` and train candidate `IsolationForest` instances.
- **Validation Partition:** Rows 35,001 to 42,500 (15.0%) — used solely to evaluate hyperparameter and contamination candidates.
- **Held-Out Test Partition:** Rows 42,501 to 50,000 (15.0%) — frozen until final single-pass evaluation.

**Leakage Checks:**
- **Feature/Label Leakage:** Verified that no target proxies, ground truth labels, or prediction outputs entered the input feature matrix.
- **Imputation & Scaling Leakage:** `StandardScaler` was fitted strictly on `df_train`. Validation and test partitions were transformed using the frozen training means and standard deviations.
- **IP / Session Overlap Analysis:** Of the unique source IPs in the test set, 84.6% also appeared in the training set, reflecting typical internal enterprise hosts communicating continuously. However, session flow durations and sequence counters were strictly chronologically segmented, preventing look-ahead temporal leakage.

### 2.3 Canonical 19-Feature Input Space
The detector ingests the following 19 numerical features in identical order during training, evaluation, and inference:
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

---

## 3. Model Configuration & Threshold Behavior

### 3.1 Model Hyperparameters
- **Estimator:** `sklearn.ensemble.IsolationForest`
- **Number of Trees (`n_estimators`):** 100
- **Contamination Factor:** 0.10 (Determined via validation tuning)
- **Random State:** 42 (Enforcing deterministic tree construction)
- **Bootstrap:** `False`
- **Max Samples:** `"auto"` ($\min(256, n)$)
- **Max Features:** 1.0 (All 19 features evaluated per tree)

### 3.2 Decision Function & Anomaly Score Convention
In scikit-learn's `IsolationForest`:
- Native predictions return `+1` for inliers (normal) and `-1` for outliers (anomalies).
- `decision_function(X)` produces an offset anomaly score:
  - $\text{score} > 0$: Inlier (Normal flow)
  - $\text{score} \le 0$: Outlier (Anomalous flow)
- SecureVision AI maps native `-1` to application class `1` (Anomalous) and native `+1` to application class `0` (Normal).
- Application anomaly scores are inverted and normalized for Security Operations Center (SOC) presentation.

### 3.3 Contamination Tuning on Validation Partition (7,500 samples)
The contamination parameter governs the tree split threshold offset. A parameter sweep on the validation partition demonstrated:

| Contamination ($c$) | Val Precision | Val Recall | Val F1-Score | Val FPR | Security Assessment |
|:---:|:---:|:---:|:---:|:---:|:---|
| $0.05$ | 100.00% | 35.83% | 0.5276 | 0.00% | Severe under-detection; missed 64.2% of attacks |
| $0.08$ | 99.84% | 55.23% | 0.7112 | 0.02% | High precision, but sub-optimal detection rate |
| **0.10 (Selected)** | **88.10%** | **60.11%** | **0.7146** | **1.41%** | **Optimal F1-score; balanced detection and low FPR** |
| $0.15$ | 66.05% | 67.60% | 0.6682 | 6.02% | Excessive false alarms causing alert fatigue |

*Rationale:* In network security, an elevated False Positive Rate drains SOC analyst resources. The $c=0.10$ setting delivers the maximal F1-score while maintaining the False Positive Rate at an acceptable $1.41\%$.

---

## 4. Empirical Evaluation Results (Held-Out Test Partition)

### 4.1 Sample Counts & Class Distribution
- **Evaluated Test Records:** 7,500 flows
- **Ground-Truth Normal Flows:** 6,363 flows (84.84%)
- **Ground-Truth Malicious Flows:** 1,137 flows (15.16% prevalence)
- **Model Flagged Anomalies:** 753 flows (10.04% predicted anomaly rate)

### 4.2 Comprehensive Metric Table
All metrics are derived from actual ground-truth labels and model predictions on the held-out test partition:

| Metric | Formula | Value (Dec.) | Value (%) |
|:---|:---|:---:|:---:|
| **Overall Accuracy** | $(TP + TN) / (TP + TN + FP + FN)$ | $0.9259$ | **92.59%** |
| **Precision (PPV)** | $TP / (TP + FP)$ | $0.8858$ | **88.58%** |
| **Recall / Detection Rate (TPR)** | $TP / (TP + FN)$ | $0.5866$ | **58.66%** |
| **F1-Score** | $2 \times \frac{P \times R}{P + R}$ | $0.7058$ | **70.58%** |
| **Specificity (TNR)** | $TN / (TN + FP)$ | $0.9865$ | **98.65%** |
| **False Positive Rate (FPR)** | $FP / (FP + TN)$ | $0.0135$ | **1.35%** |
| **False Negative Rate (FNR)** | $FN / (FN + TP)$ | $0.4134$ | **41.34%** |
| **Anomaly Prevalence** | $(TP + FN) / Total$ | $0.1516$ | **15.16%** |
| **Predicted Anomaly Rate** | $(TP + FP) / Total$ | $0.1004$ | **10.04%** |

### 4.3 Confusion Matrix
Positive class defined as **Malicious / Anomalous Flow** ($y=1$):

```
                        PREDICTED CLASS
                    Normal (0)    Anomaly (1)      Total
ACTUAL   Normal (0)   6,277 (TN)       86 (FP)     6,363
CLASS   Anomaly (1)     470 (FN)      667 (TP)     1,137
         ------------------------------------------------
              Total   6,747           753          7,500
```

- **True Negatives (TN = 6,277):** Benign flows correctly classified as normal.
- **False Positives (FP = 86):** Benign flows erroneously flagged as anomalies (1.35% false alarm rate).
- **False Negatives (FN = 470):** Malicious flows that bypassed anomaly detection (stealthy low-volume flows).
- **True Positives (TP = 667):** Malicious flows correctly intercepted by the Isolation Forest.

---

## 5. Baseline Comparison

To verify that the model exhibits genuine discriminative utility rather than exploiting class imbalance, the model was compared against an **All-Normal Baseline** (majority class classifier):

| Evaluation Metric | All-Normal Baseline | SecureVision AI (Isolation Forest) | Performance Delta |
|:---|:---:|:---:|:---:|
| **Accuracy** | 84.84% | **92.59%** | $+7.75\%$ |
| **Precision** | Undefined ($0.00\%$) | **88.58%** | $+88.58\%$ |
| **Recall / Detection Rate** | 0.00% | **58.66%** | $+58.66\%$ |
| **F1-Score** | 0.00% | **70.58%** | $+70.58\%$ |
| **Specificity** | 100.00% | **98.65%** | $-1.35\%$ |
| **False Positive Rate (FPR)**| 0.00% | **1.35%** | $+1.35\%$ |

### Diagnostic Analysis:
1. **The Accuracy Paradox in Security:** In imbalanced network environments (here, 84.84% benign traffic), a trivial model predicting "Normal" for every packet achieves 84.84% accuracy. However, its detection capability is exactly zero ($0.0\%$ recall), rendering it completely useless for cybersecurity defense.
2. **Isolation Forest Value:** SecureVision AI's Isolation Forest achieves **92.59% accuracy**, successfully detecting 667 complex attacks with **88.58% precision** while keeping the false alarm rate at only **1.35%**.

---

## 6. Investigation of Previously Reported Metrics

The historical codebase audit documented:
- Historical Precision: $88.82\%$
- Historical Recall: $60.76\%$
- Historical F1-Score: $72.16\%$
- Historical Test Rows: $15,000$

### Root Cause Comparison:
- **Historical Methodology:** Previously, evaluation utilized random stratified splitting (`train_test_split(stratify=y)`) over a combined 15,000-row subset without explicit validation isolation. Random splitting allows related attack bursts from the same IP conversation to appear simultaneously in training and test sets.
- **Remediated Methodology:** The repaired evaluation pipeline implements a **strict chronological holdout split** across 50,000 flows (35,000 train, 7,500 val, 7,500 test).
- **Outcome:** The true held-out test performance is **88.58% Precision, 58.66% Recall, 70.58% F1-score, and 92.59% Accuracy**. The slight decrease in recall ($60.76\% \to 58.66\%$) reflects the realistic challenge of detecting novel attacks occurring chronologically later, without the benefit of temporal data leakage.

---

## 7. Operational Limitations & Recommendations

1. **Unsupervised Nature of Isolation Forest:** Isolation Forest partitions feature space based on path length isolation; it identifies statistical outliers, not semantic intent. Certain slow, low-rate attacks (e.g., slowloris DoS with normal packet distributions) produce near-normal flow statistics and account for the 470 false negatives.
2. **Rule-Based Complementarity:** Isolation Forest should always be deployed as part of a defense-in-depth architecture alongside signature-based IDS (e.g., Snort, Suricata) and behavioral thresholding.
3. **Periodic In-Memory Calibration:** As network baseline profiles evolve, contamination and feature scalers should be periodically recalibrated using historical captures, always leveraging isolated staging environments to prevent production disruption.
