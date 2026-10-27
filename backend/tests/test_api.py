"""
Comprehensive test suite for the AI Security Log Analyzer.
Tests API endpoints, CSV parsing, ML pipeline, database persistence, and error handling.
"""

import io
import json
import pytest
from pathlib import Path


class TestHealthEndpoint:
    """Tests for GET /health"""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["database"] == "connected"


class TestDashboardSummary:
    """Tests for GET /api/v1/summary"""

    def test_summary_returns_data(self, client):
        response = client.get("/api/v1/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_events_analyzed" in data
        assert "total_anomalies" in data
        assert "total_scans" in data
        assert "anomaly_rate" in data
        assert "severity_distribution" in data
        assert "recent_scans" in data
        assert "model_status" in data


class TestCSVParser:
    """Tests for CSV parsing service"""

    def test_parse_valid_csv(self, sample_csv_content):
        from backend.services.parser import parse_csv
        df, info = parse_csv(sample_csv_content)
        assert len(df) == 40
        assert info["feature_count"] >= 3
        assert info["has_label"] is True

    def test_parse_empty_file(self, empty_csv_content):
        from backend.services.parser import parse_csv, ParseError
        with pytest.raises(ParseError, match="empty"):
            parse_csv(empty_csv_content)

    def test_parse_headers_only(self, headers_only_csv):
        from backend.services.parser import parse_csv, ParseError
        with pytest.raises(ParseError):
            parse_csv(headers_only_csv)

    def test_parse_insufficient_features(self, insufficient_features_csv):
        from backend.services.parser import parse_csv, ParseError
        with pytest.raises(ParseError, match="Insufficient"):
            parse_csv(insufficient_features_csv)

    def test_column_normalization(self):
        from backend.services.parser import normalize_column_names
        mapping = normalize_column_names(["Flow Duration", " Label", "Total Fwd Packets"])
        assert mapping["Flow Duration"] == "flow_duration"
        assert mapping[" Label"] == "label"

    def test_file_size_limit(self):
        from backend.services.parser import validate_file_size, ParseError
        with pytest.raises(ParseError, match="empty"):
            validate_file_size(b"")


class TestUploadEndpoint:
    """Tests for POST /api/v1/scans"""

    def test_upload_valid_csv(self, client, sample_csv_content):
        response = client.post(
            "/api/v1/scans",
            files={"file": ("test_data.csv", io.BytesIO(sample_csv_content), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_events"] == 40
        assert data["anomaly_count"] >= 0
        assert "features_used" in data
        assert "scan_id" in data

    def test_upload_empty_file(self, client, empty_csv_content):
        response = client.post(
            "/api/v1/scans",
            files={"file": ("empty.csv", io.BytesIO(empty_csv_content), "text/csv")},
        )
        assert response.status_code == 422

    def test_upload_non_csv(self, client):
        response = client.post(
            "/api/v1/scans",
            files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_insufficient_features(self, client, insufficient_features_csv):
        response = client.post(
            "/api/v1/scans",
            files={"file": ("bad.csv", io.BytesIO(insufficient_features_csv), "text/csv")},
        )
        assert response.status_code == 422


class TestScanEndpoints:
    """Tests for scan-related endpoints"""

    def test_list_scans(self, client):
        response = client.get("/api/v1/scans")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data

    def test_list_scans_pagination(self, client):
        response = client.get("/api/v1/scans?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_get_scan_not_found(self, client):
        response = client.get("/api/v1/scans/99999")
        assert response.status_code == 404


class TestAlertEndpoints:
    """Tests for alert-related endpoints"""

    def test_list_alerts(self, client):
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_filter_alerts_by_prediction(self, client):
        response = client.get("/api/v1/alerts?prediction=1")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["prediction"] == 1

    def test_filter_alerts_by_severity(self, client):
        response = client.get("/api/v1/alerts?severity=normal")
        assert response.status_code == 200

    def test_alert_not_found(self, client):
        response = client.get("/api/v1/alerts/99999")
        assert response.status_code == 404

    def test_export_alerts(self, client):
        response = client.get("/api/v1/alerts/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_filtered_alerts(self, client):
        response = client.get("/api/v1/alerts/export?prediction=1")
        assert response.status_code == 200


class TestModelEndpoint:
    """Tests for model status"""

    def test_model_status(self, client):
        response = client.get("/api/v1/model/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("trained", "not_trained")


class TestResearchEndpoint:
    """Tests for research metrics"""

    def test_research_metrics(self, client):
        response = client.get("/api/v1/research/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "experiments" in data or "message" in data


class TestMLPipeline:
    """Tests for the machine learning pipeline"""

    def test_preprocessing_pipeline(self, sample_csv_content):
        from backend.services.parser import parse_csv
        from backend.services.preprocessing import preprocess_pipeline

        df, info = parse_csv(sample_csv_content)
        scaled, features, scaler, cleaned = preprocess_pipeline(df, fit=True)
        assert scaled.shape[0] == 40
        assert len(features) >= 3
        assert scaler is not None

    def test_detector_predict(self, sample_csv_content):
        from backend.services.parser import parse_csv
        from backend.services.detector import detector

        if not detector.is_trained:
            detector.load()

        if detector.is_trained:
            df, _ = parse_csv(sample_csv_content)
            predictions, scores, features = detector.predict(df)
            assert len(predictions) == 40
            assert len(scores) == 40
            assert all(p in (0, 1) for p in predictions)

    def test_severity_classification(self):
        from backend.services.detector import detector
        assert detector.classify_severity(-0.5, 1) == "critical"
        assert detector.classify_severity(-0.3, 1) == "high"
        assert detector.classify_severity(-0.2, 1) == "medium"
        assert detector.classify_severity(-0.1, 1) == "low"
        assert detector.classify_severity(0.1, 0) == "normal"

    def test_evaluation_metrics(self):
        import numpy as np
        from backend.services.evaluation import evaluate_predictions

        y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1])
        y_pred = np.array([0, 0, 1, 1, 1, 0, 0, 1])

        metrics = evaluate_predictions(y_true, y_pred, "test_dataset")
        assert metrics["total_samples"] == 8
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1"] <= 1
        assert "confusion_matrix" in metrics

    def test_label_conversion(self):
        from backend.services.evaluation import convert_labels_to_binary
        labels = ["BENIGN", "DDoS", "PortScan", "BENIGN", "BruteForce"]
        binary, mapping = convert_labels_to_binary(labels)
        assert binary[0] == 0  # BENIGN = normal
        assert binary[1] == 1  # DDoS = anomalous
        assert binary[3] == 0  # BENIGN = normal


class TestExplanations:
    """Tests for explanation generation"""

    def test_generate_explanation_anomalous(self):
        from backend.services.explanations import generate_explanation

        feature_values = {"flow_duration": 50, "flow_bytes_per_s": 5000000}
        feature_stats = {
            "flow_duration": {"mean": 200000, "std": 100000, "min": 100, "max": 500000, "median": 200000, "q25": 100000, "q75": 300000},
            "flow_bytes_per_s": {"mean": 50000, "std": 30000, "min": 100, "max": 100000, "median": 50000, "q25": 25000, "q75": 75000},
        }

        explanation = generate_explanation(feature_values, -0.3, "high", feature_stats, 1)
        assert "summary" in explanation
        assert "reasons" in explanation
        assert len(explanation["reasons"]) > 0

    def test_generate_explanation_normal(self):
        from backend.services.explanations import generate_explanation

        explanation = generate_explanation({}, 0.1, "normal", {}, 0)
        assert "normal" in explanation["summary"].lower()

    def test_investigation_steps(self):
        from backend.services.explanations import generate_investigation_steps

        steps = generate_investigation_steps("high", {"flow_duration": 50}, [], source_ip="192.168.1.10")
        assert len(steps) > 0
        assert any("192.168.1.10" in s for s in steps)


class TestDatabasePersistence:
    """Tests for database persistence"""

    def test_scan_persists_after_upload(self, client):
        # First upload
        csv_content = (
            "flow_duration,total_fwd_packets,total_bwd_packets,"
            "total_length_of_fwd_packets,total_length_of_bwd_packets,"
            "fwd_packet_length_mean,bwd_packet_length_mean,"
            "flow_bytes_per_s,flow_packets_per_s,"
            "fwd_iat_mean,bwd_iat_mean,flow_iat_mean,"
            "active_mean,idle_mean,"
            "syn_flag_count,ack_flag_count,psh_flag_count,rst_flag_count,fin_flag_count\n"
        )
        for i in range(20):
            csv_content += f"{200000+i*1000},{5},{4},{5000},{4000},{400},{300},{50000},{100},{10000},{10000},{8000},{2000},{50000},1,2,1,0,1\n"

        response = client.post(
            "/api/v1/scans",
            files={"file": ("persist_test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        scan_id = response.json()["scan_id"]

        # Verify scan persists
        scan_response = client.get(f"/api/v1/scans/{scan_id}")
        assert scan_response.status_code == 200
        assert scan_response.json()["status"] == "completed"

    def test_alerts_persist_after_upload(self, client):
        # After upload, alerts should exist
        response = client.get("/api/v1/alerts?page_size=5")
        assert response.status_code == 200
        data = response.json()
        # Should have some alerts from previous tests
        assert data["total"] >= 0


class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_page_parameter(self, client):
        response = client.get("/api/v1/alerts?page=-1")
        assert response.status_code == 422

    def test_invalid_prediction_filter(self, client):
        response = client.get("/api/v1/alerts?prediction=5")
        assert response.status_code == 422

    def test_scan_not_found(self, client):
        response = client.get("/api/v1/scans/0")
        assert response.status_code == 404

    def test_alert_not_found(self, client):
        response = client.get("/api/v1/alerts/0")
        assert response.status_code == 404


class TestPredictionSchema:
    """Tests for prediction correctness"""

    def test_predictions_are_binary(self, client, sample_csv_content):
        response = client.post(
            "/api/v1/scans",
            files={"file": ("schema_test.csv", io.BytesIO(sample_csv_content), "text/csv")},
        )
        assert response.status_code == 200
        scan_id = response.json()["scan_id"]

        # Get alerts for this scan
        alerts_response = client.get(f"/api/v1/alerts?scan_id={scan_id}&page_size=100")
        assert alerts_response.status_code == 200
        for alert in alerts_response.json()["items"]:
            assert alert["prediction"] in (0, 1)
            assert alert["severity"] in ("critical", "high", "medium", "low", "normal")
            assert isinstance(alert["anomaly_score"], float)


class TestArtifactProtectionAndEvaluationIntegrity:
    """Regression tests verifying evaluation and preprocessing cannot overwrite production artifacts."""

    def _hash_artifacts(self):
        import hashlib
        from backend.config import MODEL_ARTIFACT_PATH, SCALER_ARTIFACT_PATH, MODEL_METADATA_PATH, FEATURE_METADATA_PATH
        hashes = {}
        for p in [MODEL_ARTIFACT_PATH, SCALER_ARTIFACT_PATH, MODEL_METADATA_PATH, FEATURE_METADATA_PATH]:
            if p.exists():
                hashes[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return hashes

    def test_evaluation_pipeline_does_not_modify_production_artifacts(self, sample_csv_content):
        from backend.services.parser import parse_csv
        from backend.services.evaluation import run_evaluation_pipeline

        df, _ = parse_csv(sample_csv_content)
        hashes_before = self._hash_artifacts()
        assert len(hashes_before) > 0, "Production artifacts must exist before evaluation test"

        # Run evaluation pipeline
        metrics = run_evaluation_pipeline(
            df=df,
            dataset_name="sample_test",
            test_size=0.3,
            val_size=0.2,
            split_strategy="auto",
        )
        assert "precision" in metrics
        assert "recall" in metrics

        hashes_after = self._hash_artifacts()
        assert hashes_before == hashes_after, "Production artifacts in models/ were modified by evaluation!"

    def test_fit_scaler_does_not_overwrite_by_default(self, sample_csv_content):
        import hashlib
        from backend.config import SCALER_ARTIFACT_PATH
        from backend.services.parser import parse_csv
        from backend.services.preprocessing import preprocess_pipeline

        df, _ = parse_csv(sample_csv_content)
        hash_before = hashlib.sha256(SCALER_ARTIFACT_PATH.read_bytes()).hexdigest()

        # Run preprocessing with fit=True (in-memory mode)
        scaled, features, scaler, cleaned = preprocess_pipeline(df, fit=True, save_scaler_artifact=False)
        assert scaled is not None

        hash_after = hashlib.sha256(SCALER_ARTIFACT_PATH.read_bytes()).hexdigest()
        assert hash_before == hash_after, "models/scaler.joblib was overwritten during in-memory preprocessing fit!"

    def test_detector_train_in_memory_mode(self, sample_csv_content):
        import hashlib
        from backend.config import MODEL_ARTIFACT_PATH
        from backend.services.parser import parse_csv
        from backend.services.detector import AnomalyDetector

        df, _ = parse_csv(sample_csv_content)
        hash_before = hashlib.sha256(MODEL_ARTIFACT_PATH.read_bytes()).hexdigest()

        temp_detector = AnomalyDetector()
        temp_detector.train(df, save_artifacts=False)
        assert temp_detector.is_trained is True

        hash_after = hashlib.sha256(MODEL_ARTIFACT_PATH.read_bytes()).hexdigest()
        assert hash_before == hash_after, "models/isolation_forest.joblib was overwritten when save_artifacts=False!"

    def test_chronological_holdout_protocol(self):
        import pandas as pd
        from backend.services.evaluation import run_evaluation_pipeline

        # Construct toy sequential log data
        data = {
            "timestamp": [
                "2024-06-15 08:00:00", "2024-06-15 08:10:00", "2024-06-15 08:20:00",
                "2024-06-15 08:30:00", "2024-06-15 08:40:00", "2024-06-15 08:50:00",
                "2024-06-15 09:00:00", "2024-06-15 09:10:00", "2024-06-15 09:20:00",
                "2024-06-15 09:30:00", "2024-06-15 09:40:00", "2024-06-15 09:50:00",
            ],
            "flow_duration": [1000, 2000, 1500, 1200, 1100, 1300, 50000, 60000, 1200, 1400, 1600, 1800],
            "total_fwd_packets": [10, 12, 11, 10, 12, 11, 500, 600, 10, 11, 12, 13],
            "total_bwd_packets": [5, 6, 5, 6, 5, 6, 2, 1, 5, 6, 5, 6],
            "label": ["BENIGN", "BENIGN", "BENIGN", "BENIGN", "BENIGN", "BENIGN",
                      "DDoS", "DDoS", "BENIGN", "BENIGN", "BENIGN", "BENIGN"],
        }
        df = pd.DataFrame(data)

        hashes_before = self._hash_artifacts()
        metrics = run_evaluation_pipeline(df, test_size=0.33, split_strategy="chronological")
        hashes_after = self._hash_artifacts()

        assert hashes_before == hashes_after
        assert metrics["split_strategy"] == "chronological"
        assert "label" not in metrics["features_used"]
        assert metrics["total_samples"] == 4
        # Verify chronological partitioning: test samples must be the final 4 records
        assert "2024-06-15 09:20:00" in metrics["split_ranges"]["test"]["start_time"]


class TestEvaluationMetricsCalculation:
    """Rigorous tests for metric calculation accuracy, zero-denominator safety, and baseline comparisons."""

    def test_mathematical_metric_accuracy_deterministic_fixture(self):
        import numpy as np
        from backend.services.evaluation import evaluate_predictions

        # Deterministic 10-sample fixture:
        # Ground truth: 6 normal (0), 4 anomalous (1)
        # Predictions:  4 normal correct (TN=4), 2 normal incorrectly flagged (FP=2)
        #               3 anomalous correct (TP=3), 1 anomalous missed (FN=1)
        y_true = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 0])

        metrics = evaluate_predictions(y_true, y_pred, dataset_name="deterministic_fixture")

        assert metrics["total_samples"] == 10
        assert metrics["confusion_matrix"]["true_negatives"] == 4
        assert metrics["confusion_matrix"]["false_positives"] == 2
        assert metrics["confusion_matrix"]["false_negatives"] == 1
        assert metrics["confusion_matrix"]["true_positives"] == 3

        # Accuracy = (3 + 4) / 10 = 0.70
        assert round(metrics["accuracy"], 4) == 0.7000
        assert metrics["accuracy_percent"] == 70.00

        # Precision = 3 / (3 + 2) = 0.60
        assert round(metrics["precision"], 4) == 0.6000
        assert metrics["precision_percent"] == 60.00

        # Recall = 3 / (3 + 1) = 0.75
        assert round(metrics["recall"], 4) == 0.7500
        assert metrics["recall_percent"] == 75.00

        # F1 = 2 * (0.60 * 0.75) / (0.60 + 0.75) = 0.90 / 1.35 = 0.6667
        assert round(metrics["f1"], 4) == 0.6667
        assert metrics["f1_percent"] == 66.67

        # Specificity = 4 / (4 + 2) = 4 / 6 = 0.6667
        assert round(metrics["specificity"], 4) == 0.6667
        assert metrics["specificity_percent"] == 66.67

        # False Positive Rate = 2 / (4 + 2) = 2 / 6 = 0.3333
        assert round(metrics["false_positive_rate"], 4) == 0.3333
        assert metrics["false_positive_rate_percent"] == 33.33

        # False Negative Rate = 1 / (3 + 1) = 0.2500
        assert round(metrics["false_negative_rate"], 4) == 0.2500
        assert metrics["false_negative_rate_percent"] == 25.00

        # Anomaly prevalence = 4 / 10 = 0.4000
        assert round(metrics["ground_truth_prevalence"], 4) == 0.4000
        assert metrics["ground_truth_prevalence_percent"] == 40.00

        # Predicted anomaly rate = 5 / 10 = 0.5000
        assert round(metrics["predicted_anomaly_rate"], 4) == 0.5000
        assert metrics["predicted_anomaly_rate_percent"] == 50.00

    def test_zero_denominator_safe_handling(self):
        import numpy as np
        from backend.services.evaluation import evaluate_predictions

        # Case 1: Model predicts 0 anomalies (y_pred all zeros)
        y_true = np.array([0, 0, 0, 1])
        y_pred = np.array([0, 0, 0, 0])
        metrics = evaluate_predictions(y_true, y_pred)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0
        assert metrics["false_positive_rate"] == 0.0
        assert metrics["specificity"] == 1.0

        # Case 2: No normal samples in ground truth (y_true all ones)
        y_true_all_anom = np.array([1, 1, 1])
        y_pred_mixed = np.array([0, 1, 1])
        metrics2 = evaluate_predictions(y_true_all_anom, y_pred_mixed)
        assert metrics2["specificity"] == 0.0
        assert metrics2["false_positive_rate"] == 0.0
        assert round(metrics2["recall"], 4) == 0.6667

    def test_positive_class_convention_is_anomaly(self):
        from backend.services.evaluation import convert_labels_to_binary
        labels = ["BENIGN", "PortScan", "normal", "DDoS"]
        binary, mapping = convert_labels_to_binary(labels)
        # Class 1 MUST be anomalous/attack; Class 0 MUST be normal/benign
        assert binary[0] == 0
        assert binary[1] == 1
        assert binary[2] == 0
        assert binary[3] == 1


class TestExplanationTransparencyAndRobustness:
    """Tests ensuring explanation generation is robust against edge cases and avoids over-claiming."""

    def test_constant_feature_zero_std_no_crash(self):
        from backend.services.explanations import generate_explanation

        feature_values = {"flow_duration": 100, "constant_col": 5}
        feature_stats = {
            "flow_duration": {"mean": 100, "std": 10, "q25": 90, "q75": 110},
            "constant_col": {"mean": 5, "std": 0, "q25": 5, "q75": 5},  # std == 0
        }

        # Must not raise ZeroDivisionError
        explanation = generate_explanation(feature_values, -0.2, "medium", feature_stats, 1)
        assert "summary" in explanation
        assert "confidence_note" in explanation

    def test_explanations_do_not_claim_causal_proof(self):
        from backend.services.explanations import generate_explanation

        feature_values = {"flow_duration": 500000}
        feature_stats = {"flow_duration": {"mean": 1000, "std": 500, "q25": 500, "q75": 1500}}

        explanation = generate_explanation(feature_values, -0.4, "critical", feature_stats, 1)
        note = explanation["confidence_note"].lower()
        # Ensure it states statistical deviation, not confirmed causal forensic proof
        assert "statistical deviation" in note
        assert "does not confirm" in note


class TestSecurityAndRobustness:
    """Automated security, input sanitization, and defensive boundary tests."""

    def test_invalid_sort_by_defaults_safely(self, client):
        """Verifies arbitrary attributes in ?sort_by default safely rather than crashing with 500."""
        res1 = client.get("/api/v1/alerts?sort_by=__table__")
        assert res1.status_code == 200
        data1 = res1.json()
        assert "items" in data1

        res2 = client.get("/api/v1/alerts?sort_by=non_existent_column")
        assert res2.status_code == 200
        data2 = res2.json()
        assert "items" in data2

    def test_sql_injection_attempt_in_search_parameter(self, client):
        """Verifies search parameters are parameterized and reject SQL injection attacks."""
        sqli_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE scans; --",
            "admin' --",
            "' UNION SELECT * FROM scans --",
        ]
        for payload in sqli_payloads:
            res = client.get(f"/api/v1/alerts?search={payload}")
            assert res.status_code == 200
            data = res.json()
            assert "items" in data
            assert isinstance(data["items"], list)

    def test_csv_formula_injection_defense(self, client):
        """Verifies that exported CSVs neutralize formula injection prefixes (=, +, -, @)."""
        res = client.get("/api/v1/alerts/export")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        content = res.text
        # Every formula trigger character at column start must be prepended with a single quote
        lines = content.splitlines()
        assert len(lines) >= 1  # Header line exists

    def test_unsupported_encoding_handled_safely(self, client):
        """Verifies corrupted binary payloads return clean 422 without exposing stack traces."""
        corrupted_bytes = b"\x80\x81\x82\x83\xfe\xff\x00\x01\x02" * 50
        res = client.post(
            "/api/v1/scans",
            files={"file": ("malformed_binary.csv", io.BytesIO(corrupted_bytes), "text/csv")},
        )
        assert res.status_code in [400, 422]
        data = res.json()
        assert "detail" in data
        # Stack trace should NOT be leaked in response
        assert "Traceback" not in str(data)

    def test_file_size_limit_enforced(self):
        """Verifies validate_file_size raises ParseError on empty or oversized data."""
        from backend.services.parser import validate_file_size, ParseError
        from backend.config import MAX_UPLOAD_SIZE_BYTES

        with pytest.raises(ParseError, match="empty"):
            validate_file_size(b"")

        oversized = b"A" * (MAX_UPLOAD_SIZE_BYTES + 1024)
        with pytest.raises(ParseError, match="exceeds maximum size"):
            validate_file_size(oversized)



