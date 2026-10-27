"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# --- Scan schemas ---
class ScanCreate(BaseModel):
    """Response after initiating a scan."""
    filename: str
    status: str
    message: str


class ScanSummary(BaseModel):
    """Brief scan info for list views."""
    id: int
    filename: str
    status: str
    total_events: int
    anomaly_count: int
    normal_count: int
    model_version: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScanDetail(ScanSummary):
    """Full scan details including features and errors."""
    features_used: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Alert schemas ---
class AlertSummary(BaseModel):
    """Brief alert info for list views."""
    id: int
    scan_id: int
    event_index: int
    timestamp: Optional[str] = None
    prediction: int
    anomaly_score: float
    severity: Optional[str] = None
    original_label: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    protocol: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertDetail(AlertSummary):
    """Full alert details with explanation."""
    feature_values: Optional[str] = None
    explanation: Optional[str] = None
    investigation_steps: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Dashboard schemas ---
class DashboardSummary(BaseModel):
    """Main dashboard statistics."""
    total_events_analyzed: int = 0
    total_anomalies: int = 0
    total_normal: int = 0
    total_scans: int = 0
    anomaly_rate: float = 0.0
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    recent_scans: List[ScanSummary] = Field(default_factory=list)
    model_status: str = "not_trained"
    dataset_info: Dict[str, Any] = Field(default_factory=dict)


# --- Model schemas ---
class ModelStatus(BaseModel):
    """Model readiness and configuration."""
    status: str  # trained, not_trained, error
    model_type: Optional[str] = None
    version: Optional[str] = None
    features: Optional[List[str]] = None
    contamination: Optional[float] = None
    n_estimators: Optional[int] = None
    training_samples: Optional[int] = None
    training_dataset: Optional[str] = None
    last_trained: Optional[datetime] = None


# --- Research schemas ---
class ResearchMetrics(BaseModel):
    """Evaluation metrics from research experiments."""
    experiment_name: str
    model_type: str
    dataset_name: Optional[str] = None
    total_samples: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    false_positive_rate: Optional[float] = None
    confusion_matrix: Optional[Dict[str, Any]] = None
    class_distribution: Optional[Dict[str, int]] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# --- Generic response schemas ---
class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    model: str
