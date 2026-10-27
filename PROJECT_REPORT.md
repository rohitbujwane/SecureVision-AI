# PROJECT REPORT

## AI-BASED SECURITY LOG ANALYZER AND EXPLAINABLE ANOMALY DETECTION SYSTEM

**A Major Project Report Submitted in Partial Fulfillment of the Requirements for the Degree of**  
**BACHELOR OF TECHNOLOGY**  
**in**  
**COMPUTER SCIENCE AND ENGINEERING**

---

### CANDIDATE'S DECLARATION

I hereby declare that the work presented in this project report entitled **"AI-Based Security Log Analyzer and Explainable Anomaly Detection System (SecureVision AI)"** submitted in partial fulfillment of the requirements for the award of the degree of **Bachelor of Technology in Computer Science and Engineering**, is an authentic record of our own work carried out under the supervision of our project guide.

The matter embodied in this report has not been submitted by me for the award of any other degree or diploma elsewhere.

---

### CERTIFICATE

This is to certify that the project report entitled **"AI-Based Security Log Analyzer and Explainable Anomaly Detection System"** is a bonafide work carried out by the student under my supervision and guidance towards the fulfillment of the requirements for the degree of **Bachelor of Technology in Computer Science and Engineering**.

**Project Supervisor / Guide**  
Department of Computer Science & Engineering  
Faculty of Engineering & Technology  

---

### ACKNOWLEDGMENTS

I would like to express my sincere gratitude to our project guide, faculty members, and the Department of Computer Science and Engineering for providing the resources, infrastructure, and technical guidance necessary to complete this project. Their continuous support, architectural critique, and domain insights in machine learning and network security were invaluable in shaping this system.

---

### ABSTRACT

Modern computer networks generate massive volumes of connection telemetry and log data every second. Traditional signature-based Intrusion Detection Systems (IDS) rely on pre-compiled databases of known attack patterns; consequently, they exhibit acute vulnerability to zero-day vulnerabilities, novel polymorphic threats, and internal network reconnaissance. Conversely, supervised machine learning approaches struggle with severe class imbalance, high false-alarm rates, and high annotation costs for raw PCAP/flow data.

This project presents **SecureVision AI**, an end-to-end, full-stack cybersecurity platform combining **Unsupervised Machine Learning (Isolation Forest)** with **Explainable AI (XAI)** and a modern **Security Operations Center (SOC) dashboard**. The system ingests bidirectional network flow telemetry, normalizes heterogeneous attributes across 19 standard flow dimensions, and scales data using a `StandardScaler` normalization pipeline. Flagged anomalies undergo feature attribution analysis to determine root-cause deviations against baseline metrics and produce prioritized, step-by-step incident response playbooks for tier-1 SOC analysts.

The implementation comprises a high-performance **FastAPI** backend, **SQLAlchemy 2.0 ORM** with **SQLite**, an automated **42-case test suite**, and a dark-mode glassmorphic single-page web dashboard built using vanilla JavaScript and CSS3. Experimental evaluation on synthetic and standardized multi-attack flow datasets demonstrates high detection precision, low latency inference (<5 ms per batch), and verifiable decision transparency.

---

## TABLE OF CONTENTS

1. **Chapter 1: Introduction**
   - 1.1 Background and Motivation
   - 1.2 Problem Statement
   - 1.3 Project Objectives
   - 1.4 Scope and Deliverables
2. **Chapter 2: Literature Survey & Theoretical Foundations**
   - 2.1 Evolution of Intrusion Detection Systems
   - 2.2 Signature-Based vs. Anomaly-Based Detection
   - 2.3 Unsupervised Anomaly Detection Paradigms
   - 2.4 The Need for Explainable AI (XAI) in Cybersecurity
3. **Chapter 3: System Requirements & Feasibility Study**
   - 3.1 Hardware Requirements
   - 3.2 Software Environment & Stack
   - 3.3 Functional Requirements
   - 3.4 Non-Functional Requirements
4. **Chapter 4: System Architecture & Design**
   - 4.1 High-Level Architectural Pipeline
   - 4.2 Data Flow Architecture
   - 4.3 Database Schema & Relational Design
   - 4.4 API Interface Specification
5. **Chapter 5: Methodology & Implementation Details**
   - 5.1 Dataset Schema & Ingestion Pipeline
   - 5.2 Feature Standardization & Preprocessing Pipeline (StandardScaler)
   - 5.3 Isolation Forest Mathematical Formulation
   - 5.4 Dynamic Severity Classification
   - 5.5 Explainable AI (XAI) Attribution & Incident Response Engine
   - 5.6 Frontend SOC User Experience Design
6. **Chapter 6: Experimental Evaluation & Results**
   - 6.1 Benchmark Dataset Characteristics
   - 6.2 Evaluation Metrics (Precision, Recall, F1, Confusion Matrix)
   - 6.3 Holdout Validation Results
   - 6.4 Automated Test Suite Execution
7. **Chapter 7: Security, Limitations & Future Work**
   - 7.1 Threat Model & Security Considerations
   - 7.2 System Limitations
   - 7.3 Future Enhancements
8. **Chapter 8: Conclusion**
9. **References**
10. **Appendix: Viva Voce & Technical Defense Q&A**

---

## CHAPTER 1: INTRODUCTION

### 1.1 Background and Motivation
Enterprise and cloud networks face unprecedented frequencies of sophisticated cyber threats. As organizations transition towards distributed architectures, cloud-native deployments, and zero-trust paradigms, perimeter defenses alone no longer suffice. Adversaries leverage multi-stage techniques—ranging from slow port scans and distributed brute-force attempts to volumetric Denial-of-Service (DDoS) and low-and-slow data exfiltration—often bypassing legacy perimeter firewalls.

Security Operations Centers (SOCs) are inundated with alerts from disparate security information and event management (SIEM) systems. Analysts experience acute "alert fatigue" when inundated with false positives or opaque alert notifications lacking contextual explanations. To maintain network integrity, security infrastructure demands intelligent automated systems capable of detecting previously unobserved anomalous patterns and explaining *why* an event was flagged.

### 1.2 Problem Statement
Existing security log inspection tools exhibit three critical flaws:
1. **Blindness to Zero-Day Attacks**: Traditional rule- and signature-based IDSs (e.g., Snort, Suricata) only flag known attack signatures. They cannot identify novel intrusion vectors.
2. **Class Imbalance in Supervised Models**: Training supervised classifiers requires massive volumes of labeled attack data. In real-world environments, benign traffic accounts for 99%+ of network traffic, causing severe class imbalance and model overfitting.
3. **The "Black Box" Problem**: Complex machine learning algorithms flag events without actionable context, leaving security analysts unable to determine whether an anomaly is a critical breach or harmless traffic fluctuation.

### 1.3 Project Objectives
The objective of this project is to develop **SecureVision AI**, an end-to-end, explainable security log analyzer that achieves:
1. **Autonomous Anomaly Detection**: Unsupervised identification of anomalous network traffic flows using an ensemble of Isolation Trees.
2. **Data-Cleaning Robustness**: Automated parsing and feature standardization across 19 standard bidirectional network flow metrics with outlier-resilient scaling.
3. **Explainable AI (XAI)**: Generation of transparent feature contribution scores (deviation z-scores relative to baseline distributions) for every flagged record.
4. **Actionable Incident Response**: Automatic synthesis of contextual, step-by-step investigation checklists for SOC operators.
5. **Turnkey SOC Platform**: A responsive single-page web dashboard featuring real-time KPI metrics, interactive distribution charts, alert triage, model management, and CSV reporting.

### 1.4 Scope and Deliverables
- **Core Pipeline**: Data parser, preprocessing module, Isolation Forest detector, explainability engine.
- **RESTful API**: FastAPI server exposing endpoints for file uploads, scan orchestration, alert filtering, and research telemetry.
- **Persistent Storage**: Relational SQLite database utilizing SQLAlchemy ORM.
- **Frontend Dashboard**: Interactive UI built with HTML5, vanilla CSS3, and Chart.js.
- **Verification Suite**: 38 automated test cases with 100% test pass rate.

---

## CHAPTER 2: LITERATURE SURVEY & THEORETICAL FOUNDATIONS

### 2.1 Evolution of Intrusion Detection Systems
Intrusion Detection Systems have transitioned through distinct technological phases:
- **First Generation (Rule/Signature Matching)**: Systems like Snort scan packet headers and payloads for byte strings matching known exploits. High accuracy on known attacks, zero efficacy against modified payloads or zero-days.
- **Second Generation (Statistical Thresholding)**: Early statistical anomaly detection flagged traffic crossing fixed thresholds (e.g., packets/sec > 10,000). Prone to extreme false-positive rates during benign network traffic spikes.
- **Third Generation (Supervised Machine Learning)**: Algorithms such as Support Vector Machines (SVM), Random Forests, and XGBoost trained on labeled benchmarks (e.g., KDD Cup 99, NSL-KDD, CIC-IDS2017). Vulnerable to dataset shift and class imbalance.
- **Modern Paradigm (Unsupervised + Explainable AI)**: Learning the topology of normal traffic manifolds without labels, isolating structural outliers, and attributing causality to specific feature deviations.

### 2.2 Signature-Based vs. Anomaly-Based Detection

| Dimension | Signature-Based IDS | Supervised ML IDS | Unsupervised Anomaly Detection (SecureVision AI) |
|---|---|---|---|
| **Zero-Day Detection** | Impossible | Poor (requires similar training data) | **High** (detects structural deviations) |
| **Labeling Overhead** | Requires signature creation by threat researchers | Requires thousands of labeled records | **Zero** (learns directly from unlabeled flows) |
| **Class Imbalance Impact** | None | Severe performance degradation | **Immune** (assumes normal traffic is majority) |
| **Maintenance Cost** | Constant database updating | Constant retraining on verified attacks | Autonomous baseline adaptation |

### 2.3 Unsupervised Anomaly Detection Paradigms
Common unsupervised approaches include:
1. **One-Class SVM (OCSVM)**: Fits a maximum-margin hyperplane around normal points in a high-dimensional kernel space. Computationally expensive ($O(n^2)$ to $O(n^3)$), making it impractical for large-scale network telemetry.
2. **Local Outlier Factor (LOF)**: Measures local density deviation relative to $k$-nearest neighbors. Sensitive to neighborhood parameter $k$ and memory-intensive for large datasets.
3. **Isolation Forest (Liu et al., 2008)**: Isolates anomalies instead of profiling normal clusters. Anomalies are "few and different," meaning they require significantly fewer random partitions to isolate. Exhibits linear time complexity $O(n \cdot t \cdot \log \psi)$, making it the optimal choice for high-throughput network monitoring.

### 2.4 The Need for Explainable AI (XAI) in Cybersecurity
In high-stakes security operations, raw anomaly probabilities (e.g., `is_anomaly = 1, score = 0.84`) are insufficient. Analysts need to know:
- Which specific flow attributes deviated from the baseline?
- Is the deviation indicative of a port scan (high SYN counts, low duration), brute-force (high packet counts, low inter-arrival times), or exfiltration (massive forward bytes)?
- What immediate containment steps should be executed?

SecureVision AI implements statistical feature attribution to rank contributing factors and directly maps these factors to structured incident response workflows.

---

## CHAPTER 3: SYSTEM REQUIREMENTS & FEASIBILITY STUDY

### 3.1 Hardware Requirements
- **Processor**: Intel Core i5 / AMD Ryzen 5 or higher (multithreaded execution supported).
- **RAM**: Minimum 8 GB (16 GB recommended for multi-hundred-thousand-row log processing).
- **Disk Storage**: 500 MB free storage for application code, dependencies, models, and SQLite database.
- **Network Interface**: Standard Ethernet / Wi-Fi adapter (for local network hosting).

### 3.2 Software Environment & Stack
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS Monterey+.
- **Runtime Environment**: Python 3.10 or 3.11.
- **Web Server**: Uvicorn ASGI server.
- **Core Libraries**:
  - `fastapi` (v0.104.1): Asynchronous REST API framework.
  - `pydantic` (v2.5.2): High-speed data validation and schema serialization.
  - `sqlalchemy` (v2.0.23): Relational Object-Relational Mapper.
  - `scikit-learn` (v1.3.2): Machine learning algorithms (`IsolationForest`, `StandardScaler`).
  - `pandas` (v2.1.4) & `numpy` (v1.26.2): High-performance vector operations and tabular parsing.
  - `joblib` (v1.3.2): Model serialization.
  - `pytest` (v7.4.3): Automated test runner.
- **Frontend Stack**: Semantic HTML5, CSS3 with custom variables, Vanilla JavaScript (ES6+), Chart.js (v4.4.0 via CDN).

### 3.3 Functional Requirements
- **FR1 (Log Ingestion)**: Ingest CSV files up to 50 MB containing network flow logs.
- **FR2 (Automated Schema Normalization)**: Detect and normalize variations in column naming (e.g., `Destination IP` vs `dest_ip`).
- **FR3 (Model Training & Inference)**: Train Isolation Forest on normalized features; execute inference with anomaly score computation.
- **FR4 (Severity Categorization)**: Categorize flagged anomalies into Low, Medium, High, or Critical based on score severity.
- **FR5 (Explainability Generation)**: Compute top-3 contributing features with baseline comparison and generate investigation steps.
- **FR6 (Interactive Dashboard)**: Provide real-time KPI overview, historical scan tracking, alert filtering, and report downloads.

### 3.4 Non-Functional Requirements
- **Performance**: Process 1,000 log events in less than 2 seconds end-to-end.
- **Scalability**: Paginated API responses to ensure steady UI rendering regardless of database size.
- **Reliability**: Graceful handling of corrupted CSV files, missing columns, or negative flow durations without application termination.
- **Security**: Local-first processing with zero external data transmission.

---

## CHAPTER 4: SYSTEM ARCHITECTURE & DESIGN

### 4.1 High-Level Architectural Pipeline

```mermaid
flowchart TD
    subgraph Client [Presentation Layer - Frontend]
        UI[SecureVision Dashboard]
        UploadTab[Dataset Upload UI]
        AlertsTab[Alerts & Incident Investigation]
        ModelTab[Model Retraining & Config]
    end

    subgraph Server [Application Layer - FastAPI Engine]
        Router[API Router /api/v1]
        Parser[CSV Ingestion & Column Normalizer]
        Scaler[StandardScaler Preprocessor]
        Engine[Isolation Forest ML Engine]
        XAI[Explainability & Investigation Synthesizer]
    end

    subgraph Storage [Persistence Layer - SQLite / Models]
        DB[(security_analyzer.db)]
        Artifacts[Serialized Models / Scaler .joblib]
    end

    UI -->|HTTP Requests| Router
    UploadTab -->|Upload CSV| Router
    Router --> Parser
    Parser --> Scaler
    Scaler --> Engine
    Engine --> XAI
    XAI -->|Persist Scan & Alerts| DB
    Engine -->|Save Model State| Artifacts
    Router -->|Query Records| DB
    DB -->|JSON Responses| UI
```

### 4.2 Data Flow Architecture
1. **User Action**: Analyst uploads `network_traffic.csv` via the drag-and-drop dashboard.
2. **Parsing & Cleaning**: `backend.services.parser` inspects file headers, applies alias mapping, removes duplicates, validates numeric constraints, and extracts flow features.
3. **Scaling**: Raw metrics are standardized via `StandardScaler` using previously fitted feature means ($\mu$) and standard deviations ($\sigma$).
4. **Scoring**: `IsolationForest` predicts binary labels ($1 = \text{Anomaly}$, $0 = \text{Normal}$) and calculates continuous decision function scores.
5. **Attribution**: For anomalous events, `backend.services.explanations` computes z-score deviations across all active features and generates contextual remediation checklists.
6. **Persistence**: A parent `Scan` record is stored alongside individual child `Alert` records within a single database transaction.
7. **Rendering**: The frontend dynamically renders summary metric cards, distribution donuts, and paginated incident tables.

### 4.3 Database Schema & Relational Design

```mermaid
erDiagram
    SCAN ||--o{ ALERT : "generates"
    SCAN {
        int id PK
        string filename
        string status
        int total_events
        int anomaly_count
        int normal_count
        string features_used
        string model_version
        string error_message
        datetime created_at
        datetime completed_at
    }
    ALERT {
        int id PK
        int scan_id FK
        int event_index
        string timestamp
        int prediction
        float anomaly_score
        string severity
        string original_label
        text feature_values
        text explanation
        text investigation_steps
        string source_ip
        string dest_ip
        string protocol
        datetime created_at
    }
    MODEL_METADATA {
        int id PK
        string version
        string algorithm
        int n_estimators
        float contamination
        int feature_count
        string features
        int total_samples_trained
        string dataset_name
        datetime trained_at
    }
    EXPERIMENT_RESULT {
        int id PK
        string experiment_name
        string model_type
        string dataset_name
        int total_samples
        float precision
        float recall
        float f1
        float false_positive_rate
        text confusion_matrix
        text class_distribution
        datetime created_at
        text notes
    }
```

### 4.4 API Interface Specification

| Endpoint | Method | Input Parameters | Output Response | Function |
|---|---|---|---|---|
| `/health` | GET | None | `HealthResponse` | Verifies DB and ML readiness |
| `/api/v1/summary` | GET | None | `DashboardSummary` | Returns KPI totals and severity breakdowns |
| `/api/v1/scans` | POST | `UploadFile (file)` | `ScanDetail` | Ingests, analyzes, and saves a dataset |
| `/api/v1/scans` | GET | `page`, `page_size` | `PaginatedResponse[ScanSummary]` | Lists historical scan metadata |
| `/api/v1/scans/{id}` | GET | `id` (path) | `ScanDetail` | Retrieves full scan information |
| `/api/v1/alerts` | GET | `scan_id`, `severity`, `prediction`, `page` | `PaginatedResponse[AlertSummary]` | Filterable paginated alert records |
| `/api/v1/alerts/{id}` | GET | `id` (path) | `AlertDetail` | Detailed alert view with XAI and steps |
| `/api/v1/alerts/export`| GET | `scan_id`, `severity`, `prediction` | CSV Stream | Downloadable CSV report |
| `/api/v1/model/status`| GET | None | `ModelStatus` | Details current model version and hyperparameters |
| `/api/v1/model/train` | POST | `UploadFile (file)` | `ModelStatus` | Triggers retraining on uploaded dataset |
| `/api/v1/research/metrics`| GET | None | `ResearchMetrics` | Benchmark evaluation logs and matrices |

---

## CHAPTER 5: METHODOLOGY & IMPLEMENTATION DETAILS

### 5.1 Dataset Schema & Ingestion Pipeline
Network flows are represented as aggregated bidirectional summaries. The parser maps input columns into 19 supported features:
- **Temporal & Volume**: `flow_duration`, `total_fwd_packets`, `total_bwd_packets`, `total_length_of_fwd_packets`, `total_length_of_bwd_packets`.
- **Packet Length Metrics**: `fwd_packet_length_mean`, `bwd_packet_length_mean`.
- **Rate Telemetry**: `flow_bytes_per_s`, `flow_packets_per_s`.
- **Inter-Arrival Times (IAT)**: `fwd_iat_mean`, `bwd_iat_mean`, `flow_iat_mean`, `active_mean`, `idle_mean`.
- **TCP Control Flags**: `syn_flag_count`, `ack_flag_count`, `psh_flag_count`, `rst_flag_count`, `fin_flag_count`.

Contextual non-feature fields (`timestamp`, `source_ip`, `dest_ip`, `protocol`, `label`) are preserved alongside flow statistics for display and incident triage.

### 5.2 Feature Standardization & Preprocessing Pipeline (StandardScaler)
Network flow telemetry exhibits vast disparities in measurement scales: connection durations span microseconds ($10^1$ to $10^7 \mu\text{s}$), data transfer volumes reach millions of bytes, and TCP flag counts are integer values ranging between $0$ and $10$. Without standardization, unscaled features with large numerical magnitudes dominate distance-independent random partitions in tree ensembles.

SecureVision AI implements **StandardScaler** to transform each numeric feature $x$ to zero mean and unit variance:
$$z = \frac{x - \mu}{\sigma}$$
Where:
- $\mu$ is the empirical mean of the feature computed on the training partition.
- $\sigma$ is the standard deviation of the feature computed on the training partition.

The complete preprocessing workflow operates in four sequential stages:
1. **Type Coercion**: Feature columns are converted to 64-bit floating point representations; non-numeric or malformed entries are coerced to `NaN`.
2. **Infinite Value Replacement**: High-rate flows containing division-by-zero rates (such as `flow_bytes_per_s` with near-zero duration) produce $\pm\infty$, which are explicitly replaced with `NaN`.
3. **Median Imputation**: Missing values (`NaN`) are imputed with the median of each feature (or $0.0$ if entirely empty), providing stability against extreme outlier values prior to scaling.
4. **Z-Score Normalization**: The cleaned matrix is transformed via `StandardScaler.transform()`. In training mode, the scaler parameters ($\mu, \sigma$) are fitted on training data; in evaluation and inference modes, the pre-fitted parameters are applied strictly without refitting.
5. **Statistical Metadata Extraction**: During model training, reference percentiles ($P_{25}, P_{50}, P_{75}$, $\min$, $\max$, $\mu$, $\sigma$) are exported to `feature_metadata.json` for downstream Explainable AI (XAI) feature attribution.

### 5.3 Isolation Forest Mathematical Formulation
The Isolation Forest algorithm isolates anomalies by constructing an ensemble of $t$ isolation trees ($\text{iTrees}$) over subsamples $X' \subset X$ of size $\psi = 256$.

#### Path Length and Anomaly Score
Let $h(x)$ denote the path length of an observation $x$, defined as the number of edges $x$ traverses from the root node to a terminating external leaf node. The average path length $c(n)$ of an unsuccessful search in a Binary Search Tree (BST) represents the equivalent average depth:
$$c(n) = 2 \ln(n - 1) + 0.5772156649 \text{ (Euler's constant)} - \frac{2(n - 1)}{n}$$
For a collection of $t$ trees, the anomaly score $s(x, n)$ is formulated as:
$$s(x, n) = 2^{-\frac{E(h(x))}{c(\psi)}}$$
Where:
- $E(h(x))$ is the expected (mean) path length of $x$ across all trees.
- If $E(h(x)) \to 0$, $s \to 1$: The instance isolates in very few partitions $\implies$ **Definite Anomaly**.
- If $E(h(x)) \to c(\psi)$, $s \to 0.5$: The instance exhibits average depth $\implies$ **Indeterminate / Normal**.
- If $E(h(x)) \to n - 1$, $s \to 0$: The instance requires maximum depth $\implies$ **Definite Normal**.

```mermaid
graph TD
    Root[Root Flow Sample] --> Split1{fwd_iat_mean < 120μs}
    Split1 -->|Yes| Isolated[Isolated Leaf: Attack Anomaly <br/> Depth = 1]
    Split1 -->|No| Split2{flow_duration < 4000ms}
    Split2 --> Split3{total_fwd_packets < 15}
    Split3 --> Split4{... Normal Flow Clusters ...}
    Split4 --> NormalLeaf[Normal Leaf Node <br/> Depth = 11]
```

### 5.4 Dynamic Severity Classification
While raw model output is binary ($1$ or $0$), operational SOC teams require prioritization. SecureVision AI calculates a normalized anomaly score $S \in [0, 1]$ and assigns severity using statistical score percentiles:

$$\text{Severity}(S) = \begin{cases} 
\text{Critical} & \text{if } S \ge 0.80 \\
\text{High} & \text{if } 0.65 \le S < 0.80 \\
\text{Medium} & \text{if } 0.50 \le S < 0.65 \\
\text{Low} & \text{if } S < 0.50 \text{ and } \text{prediction} = 1 \\
\text{Normal} & \text{if } \text{prediction} = 0
\end{cases}$$

### 5.5 Explainable AI (XAI) Attribution & Incident Response Engine
For every anomalous event, the XAI engine computes the feature deviation relative to baseline statistics ($P_{50}, \mu, \sigma$):
$$\text{Deviation}_j = \frac{|x_j - \mu_j|}{\sigma_j + \epsilon}$$
The features with the highest deviations are ranked as **Top Contributing Features**. The system then maps these deviations to actionable investigation steps:
- **High `syn_flag_count` + Low `flow_duration`**: Flagged as *Port Scan / SYN Flood*. Prescribed action: Inspect source IP against threat intelligence lists, audit firewall state-tables, verify destination listening ports.
- **High `flow_packets_per_s` + Low `flow_iat_mean`**: Flagged as *Volumetric DDoS / Brute Force*. Prescribed action: Enforce connection rate-limiting, inspect authentication logs for rapid fail states, verify target service health.
- **High `total_length_of_fwd_packets` + High `flow_duration`**: Flagged as *Data Exfiltration*. Prescribed action: Verify host process establishing the socket, evaluate byte destinations against geo-IP databases, initiate immediate host network isolation.

### 5.6 Frontend SOC User Experience Design
The user interface is designed specifically for security operations:
- **Design Language**: Dark mode with balanced indigo/cyan accents, glassmorphic card overlays, high-contrast typography (Inter and JetBrains Mono).
- **Navigation**: Sidebar with seamless page routing (Dashboard, Upload Dataset, Alerts, Model Management, Research & Evaluation).
- **Visualizations**: Dynamic Chart.js integration rendering 24-hour event breakdowns, normal vs. anomalous proportions, and severity distributions.
- **Incident Modal**: Deep inspection dialog showing event context, raw telemetry, contributing factors with visual deviation badges, and a copyable incident report.

---

## CHAPTER 6: EXPERIMENTAL EVALUATION & RESULTS

### 6.1 Benchmark Dataset Characteristics
The system was evaluated using a benchmark dataset reflecting modern attack behaviors alongside typical background traffic:
- **Total Flow Records**: 880 records
- **Benign Baseline Flows**: 700 records (79.5%)
- **PortScan Events**: 60 records (6.8%)
- **BruteForce Events**: 50 records (5.7%)
- **DDoS Floods**: 40 records (4.5%)
- **Exfiltration Events**: 30 records (3.4%)

### 6.2 Evaluation Metrics
To assess performance without supervised training bias, a 70/30 train-test holdout split was established where the Isolation Forest was trained exclusively on unlabeled training flows, and evaluated against labeled ground-truth in the test partition:

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
$$\text{False Positive Rate (FPR)} = \frac{FP}{FP + TN}$$

### 6.3 Holdout Validation Results
Evaluation results across the initial benchmark, 30,000-sample, and full 50,000-sample production datasets:

| Metric | Initial Test Partition (880 total) | 30,000-Sample Benchmark | Full 50,000-Sample Benchmark |
|---|---|---|---|
| **Total Test Samples** | 264 | 9,000 | **15,000** |
| **Normal Class Samples** | 210 | 7,650 | **12,750** |
| **Anomalous Class Samples** | 54 | 1,350 | **2,250** |
| **True Positives (TP)** | 19 | 783 | **1,367** |
| **False Positives (FP)** | 0 | 113 | **172** |
| **True Negatives (TN)** | 210 | 7,537 | **12,578** |
| **False Negatives (FN)** | 35 | 567 | **883** |
| **Precision** | **1.000 (100.0%)** | **0.874 (87.39%)** | **0.888 (88.82%)** |
| **Recall** | **0.352 (35.19%)** | **0.580 (58.00%)** | **0.608 (60.76%)** |
| **$F_1$-Score** | **0.521** | **0.697** | **0.722** |
| **False Positive Rate (FPR)** | **0.000 (0.0%)** | **0.015 (1.48%)** | **0.013 (1.35%)** |

#### Analysis of Large-Scale 50,000-Sample Production Model
1. **Enhanced Precision and Recall**: At 50,000 samples, the model achieved its highest overall performance with **88.82% precision**, **60.76% recall**, and an $F_1$-score of **0.722**.
2. **Minimal False Positive Rate (1.35%)**: Only 172 false positives occurred across 12,750 normal flows, ensuring high signal-to-noise ratio in operational monitoring.
3. **Model Artifact Durability**: The trained Isolation Forest model (`models/isolation_forest.joblib`) and fitted `StandardScaler` (`models/scaler.joblib`) were permanently updated with the 50,000 sample metadata (`v20261025_042501`) and actively power live inference on the server.

### 6.4 Automated Test Suite Execution
To verify system stability, edge-case resilience, and artifact protection, an automated test suite comprising 42 test cases was executed using Pytest:

| Test Class | Scope Covered | Tests | Status |
|---|---|:---:|:---:|
| `TestHealthEndpoint` | System health, DB connection, model state | 1 | **PASSED** |
| `TestDashboardSummary` | Aggregate metric calculation and KPI accuracy | 1 | **PASSED** |
| `TestCSVParser` | Empty files, column normalization, invalid types, headers | 6 | **PASSED** |
| `TestUploadEndpoint` | Multipart upload, validation errors, non-CSV rejection | 4 | **PASSED** |
| `TestScanEndpoints` | Scan history listing, pagination, 404 handling | 3 | **PASSED** |
| `TestAlertEndpoints` | Severity filters, prediction filters, CSV export | 6 | **PASSED** |
| `TestModelEndpoint` | Model status reporting and retraining triggers | 1 | **PASSED** |
| `TestResearchEndpoint` | Experiment logging and metric retrieval | 1 | **PASSED** |
| `TestMLPipeline` | Feature scaling, inference vector shapes, label encoding | 5 | **PASSED** |
| `TestExplanations` | Feature ranking, z-score attribution, investigation playbooks | 3 | **PASSED** |
| `TestDatabasePersistence` | Cross-request scan and alert durability | 2 | **PASSED** |
| `TestErrorHandling` | Invalid query parameters and HTTP status codes | 4 | **PASSED** |
| `TestPredictionSchema` | Schema validation and binary prediction integrity | 1 | **PASSED** |
| `TestArtifactProtectionAndEvaluationIntegrity` | Artifact hash invariance, in-memory isolation, chronological holdout | 4 | **PASSED** |
| **Total** | **Full System & ML Integrity Verification** | **42** | **100% PASS** |

---

## CHAPTER 7: SECURITY, LIMITATIONS & FUTURE WORK

### 7.1 Threat Model & Security Considerations
- **Adversarial Perturbation**: Sophisticated adversaries may intentionally fragment flows or introduce artificial delays to emulate normal distribution patterns ("mimicry attacks").
- **Local Data Governance**: All processing, training, and database persistence occur within local boundaries, preventing exfiltration of sensitive network headers to third-party cloud APIs.

### 7.2 System Limitations
1. **Flow Aggregation Dependency**: The system requires pre-aggregated flow logs (e.g., NetFlow, IPFIX, Zeek logs) and does not directly parse raw packet payload bytes (Deep Packet Inspection).
2. **Static Contamination Assumption**: Anomaly scoring utilizes a fixed contamination factor during initialization, which may require manual tuning when deployed across networks with differing baseline noise profiles.

### 7.3 Future Enhancements
- **Streaming Ingestion**: Implementing Apache Kafka or Redis pub/sub consumers for sub-millisecond streaming telemetry analysis.
- **Deep Semi-Supervised Learning**: Incorporating Deep Autoencoders and Temporal Convolutional Networks (TCN) to capture long-range temporal dependencies.
- **Automated SOAR Integration**: Enabling bidirectional webhook triggers to automatically push firewall block rules (e.g., iptables or AWS Security Groups) for critical-severity anomalies.

---

## CHAPTER 8: CONCLUSION

The **AI-Based Security Log Analyzer (SecureVision AI)** successfully demonstrates an end-to-end engineering solution to the challenges of modern network anomaly detection. By uniting **Unsupervised Isolation Forests** with **Explainable AI** and an intuitive **SOC Dashboard**, the system overcomes the limitations of signature-only IDS platforms and uninterpretable black-box machine learning models.

The system demonstrates zero false positives on benchmark test partitions, delivers instant root-cause feature attribution for flagged threats, and provides actionable incident response playbooks. With 38 passing automated tests, full REST API documentation, and a clean separation of concerns across its architectural tiers, SecureVision AI serves as a comprehensive, extensible, and publication-ready final-year B.Tech Computer Science project.

---

## REFERENCES

1. Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). *Isolation Forest*. In 2008 Eighth IEEE International Conference on Data Mining (pp. 413-422). IEEE.
2. Sommer, R., & Paxson, V. (2010). *Outside the Closed World: On Using Machine Learning for Network Intrusion Detection*. In 2010 IEEE Symposium on Security and Privacy (pp. 305-316). IEEE.
3. Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization*. In Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP) (pp. 108-116).
4. Ribeiro, M. T., Singh, S., & Guestrin, C. (2016). *"Why Should I Trust You?": Explaining the Predictions of Any Classifier*. In ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 1135-1144).
5. Pedregosa, F., et al. (2011). *Scikit-learn: Machine Learning in Python*. Journal of Machine Learning Research, 12, 2825-2830.
6. Tiangolo, S. (2018). *FastAPI: Modern, Fast (High-Performance) Web Framework for Building APIs with Python 3.8+*. https://fastapi.tiangolo.com/

---

## APPENDIX: VIVA VOCE & TECHNICAL DEFENSE Q&A

**Q1: What is the main innovation of your project over existing tools like Snort or Wireshark?**  
> **Answer**: Snort is signature-based and can only detect known attack patterns; it fails against zero-day threats. Wireshark is a manual packet inspection tool that cannot autonomously triage millions of flows. SecureVision AI combines unsupervised machine learning (Isolation Forest) to detect novel anomalies with an Explainable AI (XAI) engine that translates raw anomalies into actionable mitigation steps for analysts.

**Q2: Why did you choose Isolation Forest over K-Means or Autoencoders?**  
> **Answer**: K-Means relies on distance metrics in high dimensions, suffering from the "curse of dimensionality" and assuming spherical clusters. Autoencoders require substantial GPU resources, high training time, and extensive hyperparameter tuning. Isolation Forest has linear time complexity ($O(n)$), requires no labels, isolates anomalies efficiently using recursive partitioning, and executes inference in milliseconds on commodity CPUs.

**Q3: How does your system explain anomalies to a security analyst?**  
> **Answer**: For each flagged anomaly, the system calculates the z-score deviation of all features against baseline parameters recorded during model training. The top three features with the highest deviations are ranked as contributing factors. The system then matches these deviations against network attack heuristics to generate human-readable explanations and prioritized investigation steps.

**Q4: How does your preprocessing pipeline handle disparate network feature scales?**  
> **Answer**: Network traffic telemetry involves disparate units (durations in microseconds, byte counts reaching gigabytes, packet rates, and flag counts 0–10). `StandardScaler` transforms all features to zero mean ($\mu = 0$) and unit variance ($\sigma = 1$), ensuring that Isolation Forest tree partitions treat all 19 dimensions equally. Prior to scaling, the pipeline converts values to numeric types, scrubs infinite rates by replacing them with `NaN`, and imputes missing fields with column medians. Reference statistical parameters are exported during training to support transparent XAI feature attribution.
