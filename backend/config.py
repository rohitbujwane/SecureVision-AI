"""
Application configuration module.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
FRONTEND_DIR = BASE_DIR / "frontend"
RESEARCH_DIR = BASE_DIR / "research"

# Ensure directories exist
for d in [DATA_DIR, MODEL_DIR, RESEARCH_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Application
APP_NAME = os.getenv("APP_NAME", "AI Security Log Analyzer")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'security_analyzer.db'}")

# Upload limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_ROW_COUNT = int(os.getenv("MAX_ROW_COUNT", "500000"))

# Model configuration
MODEL_CONTAMINATION = float(os.getenv("MODEL_CONTAMINATION", "0.1"))
MODEL_N_ESTIMATORS = int(os.getenv("MODEL_N_ESTIMATORS", "100"))
MODEL_RANDOM_STATE = int(os.getenv("MODEL_RANDOM_STATE", "42"))
MODEL_ARTIFACT_PATH = MODEL_DIR / "isolation_forest.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"
SCALER_ARTIFACT_PATH = MODEL_DIR / "scaler.joblib"
FEATURE_METADATA_PATH = MODEL_DIR / "feature_metadata.json"

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")

# Feature mapping: supported numeric features for ML pipeline
SUPPORTED_FEATURES = [
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_length_of_fwd_packets",
    "total_length_of_bwd_packets",
    "fwd_packet_length_mean",
    "bwd_packet_length_mean",
    "flow_bytes_per_s",
    "flow_packets_per_s",
    "fwd_iat_mean",
    "bwd_iat_mean",
    "flow_iat_mean",
    "active_mean",
    "idle_mean",
    "syn_flag_count",
    "ack_flag_count",
    "psh_flag_count",
    "rst_flag_count",
    "fin_flag_count",
]

# Column name mapping: maps common variations to canonical names
COLUMN_NAME_MAP = {
    # Direct CIC-IDS2017 mappings
    "flow duration": "flow_duration",
    "flow_duration": "flow_duration",
    "total fwd packets": "total_fwd_packets",
    "total_fwd_packets": "total_fwd_packets",
    "total backward packets": "total_bwd_packets",
    "total bwd packets": "total_bwd_packets",
    "total_bwd_packets": "total_bwd_packets",
    "total length of fwd packets": "total_length_of_fwd_packets",
    "total_length_of_fwd_packets": "total_length_of_fwd_packets",
    "total length of bwd packets": "total_length_of_bwd_packets",
    "total_length_of_bwd_packets": "total_length_of_bwd_packets",
    "fwd packet length mean": "fwd_packet_length_mean",
    "fwd_packet_length_mean": "fwd_packet_length_mean",
    "bwd packet length mean": "bwd_packet_length_mean",
    "bwd_packet_length_mean": "bwd_packet_length_mean",
    "flow bytes/s": "flow_bytes_per_s",
    "flow_bytes_per_s": "flow_bytes_per_s",
    "flow bytes_per_s": "flow_bytes_per_s",
    "flow packets/s": "flow_packets_per_s",
    "flow_packets_per_s": "flow_packets_per_s",
    "flow packets_per_s": "flow_packets_per_s",
    "fwd iat mean": "fwd_iat_mean",
    "fwd_iat_mean": "fwd_iat_mean",
    "bwd iat mean": "bwd_iat_mean",
    "bwd_iat_mean": "bwd_iat_mean",
    "flow iat mean": "flow_iat_mean",
    "flow_iat_mean": "flow_iat_mean",
    "active mean": "active_mean",
    "active_mean": "active_mean",
    "idle mean": "idle_mean",
    "idle_mean": "idle_mean",
    "syn flag count": "syn_flag_count",
    "syn_flag_count": "syn_flag_count",
    "ack flag count": "ack_flag_count",
    "ack_flag_count": "ack_flag_count",
    "psh flag count": "psh_flag_count",
    "psh_flag_count": "psh_flag_count",
    "rst flag count": "rst_flag_count",
    "rst_flag_count": "rst_flag_count",
    "fin flag count": "fin_flag_count",
    "fin_flag_count": "fin_flag_count",
    # Label columns
    "label": "label",
    " label": "label",
}

# Minimum required features for a valid analysis
MIN_REQUIRED_FEATURES = 3

# Severity thresholds (based on anomaly scores from Isolation Forest)
# Isolation Forest scores: more negative = more anomalous
SEVERITY_THRESHOLDS = {
    "critical": -0.35,
    "high": -0.25,
    "medium": -0.15,
}
