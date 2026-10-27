"""
Anomaly detection service using Isolation Forest.
Handles model training, loading, inference, and scoring.
"""

import json
import datetime
import numpy as np
import pandas as pd
import joblib
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path
from sklearn.ensemble import IsolationForest

from backend.config import (
    MODEL_ARTIFACT_PATH, MODEL_METADATA_PATH, FEATURE_METADATA_PATH,
    MODEL_CONTAMINATION, MODEL_N_ESTIMATORS, MODEL_RANDOM_STATE,
    SEVERITY_THRESHOLDS
)
from backend.services.preprocessing import preprocess_pipeline, load_scaler


class DetectorError(Exception):
    """Raised on model-related errors."""
    pass


class AnomalyDetector:
    """
    Isolation Forest based anomaly detector.
    Manages training, persistence, and inference.
    """

    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.scaler = None
        self.features: List[str] = []
        self.version: str = "untrained"
        self.training_samples: int = 0
        self.is_trained: bool = False

    def train(self, df: pd.DataFrame, feature_list: Optional[List[str]] = None,
              dataset_name: str = "unknown", contamination: Optional[float] = None,
              save_artifacts: bool = True) -> Dict[str, Any]:
        """
        Train an Isolation Forest model on the given data.
        
        Args:
            df: DataFrame with feature columns
            feature_list: Specific features to use
            dataset_name: Name for metadata tracking
            contamination: Sensitivity factor (defaults to MODEL_CONTAMINATION)
            save_artifacts: If True, writes model and metadata to disk; if False, trains in-memory only
        
        Returns:
            Training metadata dict
        """
        contam = contamination if contamination is not None else MODEL_CONTAMINATION

        # Preprocess with fit=True to create new scaler (only saved if save_artifacts=True)
        scaled_data, used_features, scaler, cleaned_df = preprocess_pipeline(
            df, feature_list=feature_list, fit=True, save_scaler_artifact=save_artifacts
        )

        if scaled_data.shape[0] < 10:
            raise DetectorError("Need at least 10 samples to train the model.")

        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=contam,
            n_estimators=MODEL_N_ESTIMATORS,
            random_state=MODEL_RANDOM_STATE,
            n_jobs=-1,
        )
        self.model.fit(scaled_data)

        self.scaler = scaler
        self.features = used_features
        self.training_samples = scaled_data.shape[0]
        self.version = datetime.datetime.utcnow().strftime("v%Y%m%d_%H%M%S")
        self.is_trained = True

        metadata = {
            "model_type": "IsolationForest",
            "version": self.version,
            "training_samples": self.training_samples,
            "features": self.features,
            "contamination": contam,
            "n_estimators": MODEL_N_ESTIMATORS,
            "random_state": MODEL_RANDOM_STATE,
            "training_dataset": dataset_name,
            "trained_at": datetime.datetime.utcnow().isoformat(),
        }

        if save_artifacts:
            # Save model artifact
            joblib.dump(self.model, MODEL_ARTIFACT_PATH)

            # Save metadata
            with open(MODEL_METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Save feature metadata
            feature_stats = {}
            for feat in used_features:
                if feat in cleaned_df.columns:
                    col = cleaned_df[feat]
                    feature_stats[feat] = {
                        "mean": float(col.mean()),
                        "std": float(col.std()),
                        "min": float(col.min()),
                        "max": float(col.max()),
                        "median": float(col.median()),
                        "q25": float(col.quantile(0.25)),
                        "q75": float(col.quantile(0.75)),
                    }
            with open(FEATURE_METADATA_PATH, 'w') as f:
                json.dump(feature_stats, f, indent=2)

        return metadata

    def load(self) -> bool:
        """
        Load a trained model and scaler from disk.
        
        Returns:
            True if successfully loaded
        """
        if not MODEL_ARTIFACT_PATH.exists():
            return False

        try:
            self.model = joblib.load(MODEL_ARTIFACT_PATH)
            if not isinstance(self.model, IsolationForest):
                self.model = None
                return False

            self.scaler = load_scaler()

            if MODEL_METADATA_PATH.exists():
                with open(MODEL_METADATA_PATH) as f:
                    meta = json.load(f)
                self.features = meta.get("features", [])
                self.version = meta.get("version", "unknown")
                self.training_samples = meta.get("training_samples", 0)
            else:
                self.features = []
                self.version = "unknown"

            self.is_trained = True
            return True

        except Exception as e:
            self.model = None
            self.is_trained = False
            return False

    def predict(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Run inference on new data.
        
        Args:
            df: DataFrame with feature columns
        
        Returns:
            Tuple of (predictions [0=normal, 1=anomalous], anomaly_scores, features_used)
        
        Raises:
            DetectorError if model not trained or features mismatch
        """
        if not self.is_trained or self.model is None:
            raise DetectorError("Model is not trained. Please train the model first.")

        # Use the features the model was trained on
        scaled_data, used_features, _, cleaned_df = preprocess_pipeline(
            df, feature_list=self.features, scaler=self.scaler, fit=False
        )

        if len(used_features) == 0:
            raise DetectorError(
                "None of the model's expected features were found in the input data. "
                f"Expected features: {self.features}"
            )

        # If some features are missing, warn but continue
        missing = set(self.features) - set(used_features)
        if missing:
            # Pad missing features with zeros
            full_data = np.zeros((scaled_data.shape[0], len(self.features)))
            for i, feat in enumerate(self.features):
                if feat in used_features:
                    j = used_features.index(feat)
                    full_data[:, i] = scaled_data[:, j]
            scaled_data = full_data
            used_features = self.features

        # Isolation Forest: -1 = anomaly, 1 = normal
        raw_predictions = self.model.predict(scaled_data)
        anomaly_scores = self.model.decision_function(scaled_data)

        # Convert: 0 = normal, 1 = anomalous
        predictions = np.where(raw_predictions == -1, 1, 0)

        return predictions, anomaly_scores, used_features

    def classify_severity(self, anomaly_score: float, prediction: int) -> str:
        """
        Assign severity based on anomaly score.
        More negative score = more anomalous.
        """
        if prediction == 0:
            return "normal"

        if anomaly_score <= SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif anomaly_score <= SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif anomaly_score <= SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def get_feature_stats(self) -> Dict[str, Any]:
        """Load training feature statistics."""
        if FEATURE_METADATA_PATH.exists():
            with open(FEATURE_METADATA_PATH) as f:
                return json.load(f)
        return {}

    def get_status(self) -> Dict[str, Any]:
        """Get current model status."""
        status = {
            "status": "trained" if self.is_trained else "not_trained",
            "model_type": "IsolationForest" if self.is_trained else None,
            "version": self.version if self.is_trained else None,
            "features": self.features if self.is_trained else None,
            "contamination": MODEL_CONTAMINATION if self.is_trained else None,
            "n_estimators": MODEL_N_ESTIMATORS if self.is_trained else None,
            "training_samples": self.training_samples if self.is_trained else None,
        }

        if MODEL_METADATA_PATH.exists():
            with open(MODEL_METADATA_PATH) as f:
                meta = json.load(f)
            status["training_dataset"] = meta.get("training_dataset")
            status["last_trained"] = meta.get("trained_at")

        return status


# Singleton detector instance
detector = AnomalyDetector()
