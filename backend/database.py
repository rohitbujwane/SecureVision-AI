"""
Database module using SQLAlchemy for SQLite persistence.
Defines all tables, relationships, and database initialization.
"""

import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime,
    Boolean, ForeignKey, Index, event
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better concurrent read performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Scan(Base):
    """Represents a single dataset upload and analysis run."""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, failed
    total_events = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)
    normal_count = Column(Integer, default=0)
    features_used = Column(Text, nullable=True)  # JSON list of feature names
    model_version = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    alerts = relationship("Alert", back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scans_status", "status"),
        Index("ix_scans_created_at", "created_at"),
    )


class Alert(Base):
    """Represents a single analyzed event with prediction and explanation."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    event_index = Column(Integer, nullable=False)  # Row index in original CSV
    timestamp = Column(String(100), nullable=True)  # Original event timestamp if available
    prediction = Column(Integer, nullable=False)  # 0=normal, 1=anomalous
    anomaly_score = Column(Float, nullable=False)
    severity = Column(String(20), nullable=True)  # critical, high, medium, low, normal
    original_label = Column(String(100), nullable=True)  # Ground truth label if available
    feature_values = Column(Text, nullable=True)  # JSON dict of feature values
    explanation = Column(Text, nullable=True)  # JSON explanation object
    investigation_steps = Column(Text, nullable=True)  # JSON list of steps
    source_ip = Column(String(50), nullable=True)
    dest_ip = Column(String(50), nullable=True)
    protocol = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_scan_id", "scan_id"),
        Index("ix_alerts_prediction", "prediction"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_anomaly_score", "anomaly_score"),
    )


class ModelMetadata(Base):
    """Tracks model training runs and configurations."""
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    training_samples = Column(Integer, default=0)
    features = Column(Text, nullable=True)  # JSON list
    contamination = Column(Float, nullable=True)
    n_estimators = Column(Integer, nullable=True)
    training_dataset = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ExperimentResult(Base):
    """Stores evaluation experiment results."""
    __tablename__ = "experiment_results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(255), nullable=False)
    model_type = Column(String(100), nullable=False)
    dataset_name = Column(String(255), nullable=True)
    total_samples = Column(Integer, default=0)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    confusion_matrix = Column(Text, nullable=True)  # JSON
    class_distribution = Column(Text, nullable=True)  # JSON
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get a direct database session (non-generator)."""
    return SessionLocal()
