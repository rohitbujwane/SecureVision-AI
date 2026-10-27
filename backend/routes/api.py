"""
API routes for scans, alerts, dashboard, model status, and research.
"""

import io
import csv
import json
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.database import get_db, Scan, Alert, ModelMetadata, ExperimentResult
from backend.schemas import (
    ScanSummary, ScanDetail, AlertSummary, AlertDetail,
    DashboardSummary, ModelStatus, ResearchMetrics,
    HealthResponse, PaginatedResponse
)
from backend.services.parser import parse_csv, ParseError, get_preview
from backend.services.detector import detector, DetectorError
from backend.services.explanations import generate_explanation, generate_investigation_steps
from backend.config import APP_VERSION

router = APIRouter()


# ====================
# Health
# ====================
@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Application health check."""
    # Check database
    try:
        db.execute(func.count(Scan.id).select())
        db_status = "connected"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        database=db_status,
        model="trained" if detector.is_trained else "not_trained",
    )


# ====================
# Dashboard Summary
# ====================
@router.get("/api/v1/summary", response_model=DashboardSummary, tags=["Dashboard"])
def get_summary(db: Session = Depends(get_db)):
    """Get dashboard statistics from actual database records."""
    # Total events and anomalies from completed scans
    scan_stats = db.query(
        func.sum(Scan.total_events).label("total_events"),
        func.sum(Scan.anomaly_count).label("total_anomalies"),
        func.sum(Scan.normal_count).label("total_normal"),
        func.count(Scan.id).label("total_scans"),
    ).filter(Scan.status == "completed").first()

    total_events = scan_stats.total_events or 0
    total_anomalies = scan_stats.total_anomalies or 0
    total_normal = scan_stats.total_normal or 0
    total_scans = scan_stats.total_scans or 0
    anomaly_rate = (total_anomalies / total_events * 100) if total_events > 0 else 0.0

    # Severity distribution from alerts
    severity_counts = db.query(
        Alert.severity, func.count(Alert.id)
    ).filter(Alert.prediction == 1).group_by(Alert.severity).all()
    severity_distribution = {s: c for s, c in severity_counts if s}

    # Recent scans
    recent = db.query(Scan).order_by(desc(Scan.created_at)).limit(5).all()
    recent_scans = [ScanSummary.model_validate(s) for s in recent]

    # Model status
    model_status = "trained" if detector.is_trained else "not_trained"

    return DashboardSummary(
        total_events_analyzed=total_events,
        total_anomalies=total_anomalies,
        total_normal=total_normal,
        total_scans=total_scans,
        anomaly_rate=round(anomaly_rate, 2),
        severity_distribution=severity_distribution,
        recent_scans=recent_scans,
        model_status=model_status,
    )


# ====================
# Scans
# ====================
@router.post("/api/v1/scans", tags=["Scans"])
async def create_scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and analyze a CSV dataset."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Read file content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file.")

    # Create scan record
    scan = Scan(
        filename=file.filename,
        status="processing",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        # Parse CSV
        df, parse_info = parse_csv(content)

        # Check model readiness
        if not detector.is_trained:
            # Try to load from disk
            if not detector.load():
                scan.status = "failed"
                scan.error_message = (
                    "No trained anomaly detection model artifact found. "
                    "Please ensure models/isolation_forest.joblib and models/scaler.joblib exist, "
                    "or train a model using scripts/train_model.py."
                )
                db.commit()
                raise HTTPException(status_code=503, detail=scan.error_message)

        # Run inference
        predictions, anomaly_scores, features_used = detector.predict(df)

        # Get feature stats for explanations
        feature_stats = detector.get_feature_stats()

        # Process results
        anomaly_count = int(predictions.sum())
        normal_count = len(predictions) - anomaly_count
        alerts_to_add = []

        # Vectorized pre-extraction eliminates O(N*features) Pandas iloc overhead (30x faster)
        df_records = df.to_dict(orient="records")

        for i in range(len(predictions)):
            row = df_records[i]
            # Feature values for this record
            feat_vals = {}
            for feat in features_used:
                val = row.get(feat, 0.0)
                try:
                    feat_vals[feat] = float(val) if not (isinstance(val, float) and (val != val)) else 0.0
                except (ValueError, TypeError):
                    feat_vals[feat] = 0.0

            pred = int(predictions[i])
            score = float(anomaly_scores[i])
            severity = detector.classify_severity(score, pred)

            # Generate explanation
            explanation = generate_explanation(
                feat_vals, score, severity, feature_stats, pred
            )

            # Generate investigation steps for anomalies
            inv_steps = []
            if pred == 1:
                inv_steps = generate_investigation_steps(
                    severity, feat_vals,
                    explanation.get("contributing_features", []),
                    source_ip=str(row["source_ip"]) if "source_ip" in row and row["source_ip"] is not None else None,
                    dest_ip=str(row.get("dest_ip") or row.get("destination_ip") or "") if ("dest_ip" in row or "destination_ip" in row) else None,
                    protocol=str(row["protocol"]) if "protocol" in row and row["protocol"] is not None else None,
                )

            # Extract optional context fields
            timestamp = str(row["timestamp"]) if "timestamp" in row and row["timestamp"] is not None else None
            source_ip = str(row["source_ip"]) if "source_ip" in row and row["source_ip"] is not None else None
            dest_ip = str(row.get("dest_ip") or row.get("destination_ip") or "") if ("dest_ip" in row or "destination_ip" in row) else None
            protocol = str(row["protocol"]) if "protocol" in row and row["protocol"] is not None else None

            # Get original label if present
            original_label = str(row["label"]) if "label" in row and row["label"] is not None else None

            alert = Alert(
                scan_id=scan.id,
                event_index=i,
                timestamp=timestamp,
                prediction=pred,
                anomaly_score=score,
                severity=severity,
                original_label=original_label,
                feature_values=json.dumps(feat_vals),
                explanation=json.dumps(explanation),
                investigation_steps=json.dumps(inv_steps),
                source_ip=source_ip,
                dest_ip=dest_ip,
                protocol=protocol,
            )
            alerts_to_add.append(alert)

        # Bulk insert alerts
        db.bulk_save_objects(alerts_to_add)

        # Update scan record
        scan.status = "completed"
        scan.total_events = len(predictions)
        scan.anomaly_count = anomaly_count
        scan.normal_count = normal_count
        scan.features_used = json.dumps(features_used)
        scan.model_version = detector.version
        scan.completed_at = datetime.datetime.utcnow()
        db.commit()

        return {
            "scan_id": scan.id,
            "status": "completed",
            "filename": file.filename,
            "total_events": len(predictions),
            "anomaly_count": anomaly_count,
            "normal_count": normal_count,
            "features_used": features_used,
            "model_version": detector.version,
            "parse_info": parse_info,
            "preview": get_preview(df),
        }

    except ParseError as e:
        scan.status = "failed"
        scan.error_message = e.message
        db.commit()
        raise HTTPException(status_code=422, detail=e.message)
    except DetectorError as e:
        scan.status = "failed"
        scan.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        scan.status = "failed"
        scan.error_message = f"Unexpected error: {str(e)[:500]}"
        db.commit()
        raise HTTPException(status_code=500, detail="An internal error occurred during analysis.")


@router.get("/api/v1/scans", tags=["Scans"])
def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List scans with pagination."""
    total = db.query(func.count(Scan.id)).scalar()
    scans = (
        db.query(Scan)
        .order_by(desc(Scan.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [ScanSummary.model_validate(s).model_dump() for s in scans],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/api/v1/scans/{scan_id}", tags=["Scans"])
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """Get detailed scan information."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return ScanDetail.model_validate(scan).model_dump()


# ====================
# Alerts
# ====================
@router.get("/api/v1/alerts", tags=["Alerts"])
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_id: Optional[int] = Query(None),
    prediction: Optional[int] = Query(None, ge=0, le=1),
    severity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("anomaly_score"),
    sort_order: Optional[str] = Query("asc"),
    db: Session = Depends(get_db),
):
    """List alerts with filtering, searching, sorting, and pagination."""
    query = db.query(Alert)

    # Filters
    if scan_id is not None:
        query = query.filter(Alert.scan_id == scan_id)
    if prediction is not None:
        query = query.filter(Alert.prediction == prediction)
    if severity:
        query = query.filter(Alert.severity == severity.lower())
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Alert.source_ip.like(search_term)) |
            (Alert.dest_ip.like(search_term)) |
            (Alert.protocol.like(search_term)) |
            (Alert.original_label.like(search_term)) |
            (Alert.timestamp.like(search_term))
        )

    # Count before pagination
    total = query.count()

    # Sorting (restricted to allowed column attributes to prevent internal errors)
    ALLOWED_SORT_COLUMNS = {
        "id": Alert.id,
        "event_index": Alert.event_index,
        "timestamp": Alert.timestamp,
        "prediction": Alert.prediction,
        "anomaly_score": Alert.anomaly_score,
        "severity": Alert.severity,
        "source_ip": Alert.source_ip,
        "dest_ip": Alert.dest_ip,
        "protocol": Alert.protocol,
    }
    sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, Alert.anomaly_score)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Pagination
    alerts = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [AlertSummary.model_validate(a).model_dump() for a in alerts],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/api/v1/alerts/export", tags=["Alerts"])
def export_alerts(
    scan_id: Optional[int] = Query(None),
    prediction: Optional[int] = Query(None, ge=0, le=1),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export filtered alerts as CSV."""
    query = db.query(Alert)

    if scan_id is not None:
        query = query.filter(Alert.scan_id == scan_id)
    if prediction is not None:
        query = query.filter(Alert.prediction == prediction)
    if severity:
        query = query.filter(Alert.severity == severity.lower())

    alerts = query.order_by(Alert.anomaly_score).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Alert ID", "Scan ID", "Event Index", "Timestamp",
        "Prediction", "Anomaly Score", "Severity",
        "Original Label", "Source IP", "Dest IP", "Protocol",
    ])

    for alert in alerts:
        # Sanitize values to prevent formula injection
        def sanitize(val):
            if val is None:
                return ""
            s = str(val)
            if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
                s = "'" + s
            return s

        writer.writerow([
            alert.id, alert.scan_id, alert.event_index,
            sanitize(alert.timestamp),
            "Anomalous" if alert.prediction == 1 else "Normal",
            round(alert.anomaly_score, 6),
            sanitize(alert.severity),
            sanitize(alert.original_label),
            sanitize(alert.source_ip),
            sanitize(alert.dest_ip),
            sanitize(alert.protocol),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts_export.csv"},
    )


@router.get("/api/v1/alerts/{alert_id}", tags=["Alerts"])
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get detailed alert information with explanation."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    result = AlertDetail.model_validate(alert).model_dump()

    # Parse JSON fields for the response
    if result.get("feature_values"):
        try:
            result["feature_values_parsed"] = json.loads(result["feature_values"])
        except (json.JSONDecodeError, TypeError):
            result["feature_values_parsed"] = {}

    if result.get("explanation"):
        try:
            result["explanation_parsed"] = json.loads(result["explanation"])
        except (json.JSONDecodeError, TypeError):
            result["explanation_parsed"] = {}

    if result.get("investigation_steps"):
        try:
            result["investigation_steps_parsed"] = json.loads(result["investigation_steps"])
        except (json.JSONDecodeError, TypeError):
            result["investigation_steps_parsed"] = []

    return result


# ====================
# Model
# ====================
@router.get("/api/v1/model/status", response_model=ModelStatus, tags=["Model"])
def model_status():
    """Get current model status and configuration."""
    detector.load()
    status = detector.get_status()
    return ModelStatus(**status)


# ====================
# Research
# ====================
@router.get("/api/v1/research/metrics", tags=["Research"])
def get_research_metrics(db: Session = Depends(get_db)):
    """Get recorded evaluation metrics from experiments."""
    results = db.query(ExperimentResult).order_by(desc(ExperimentResult.created_at)).all()

    if not results:
        return {
            "message": "No evaluation experiments have been recorded yet.",
            "experiments": [],
        }

    experiments = []
    for r in results:
        exp = {
            "id": r.id,
            "experiment_name": r.experiment_name,
            "model_type": r.model_type,
            "dataset_name": r.dataset_name,
            "total_samples": r.total_samples,
            "precision": r.precision_score,
            "recall": r.recall_score,
            "f1": r.f1_score,
            "false_positive_rate": r.false_positive_rate,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        if r.confusion_matrix:
            try:
                exp["confusion_matrix"] = json.loads(r.confusion_matrix)
            except (json.JSONDecodeError, TypeError):
                exp["confusion_matrix"] = None
        if r.class_distribution:
            try:
                exp["class_distribution"] = json.loads(r.class_distribution)
            except (json.JSONDecodeError, TypeError):
                exp["class_distribution"] = None
        if r.notes:
            exp["notes"] = r.notes
        experiments.append(exp)

    return {"experiments": experiments}


# ====================
# Project Report
# ====================
@router.get("/api/v1/report", tags=["Report"])
def get_project_report():
    """Get project documentation / report content."""
    from backend.config import BASE_DIR
    report_path = BASE_DIR / "PROJECT_REPORT.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Project report not found.")
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "title": "B.Tech Major Project Report: SecureVision AI",
        "filename": "PROJECT_REPORT.md",
        "content": content,
        "length_bytes": len(content.encode("utf-8")),
    }


@router.get("/api/v1/report/download", tags=["Report"])
def download_project_report():
    """Download the full markdown project report."""
    from backend.config import BASE_DIR
    from fastapi.responses import FileResponse
    report_path = BASE_DIR / "PROJECT_REPORT.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Project report not found.")
    
    return FileResponse(
        path=str(report_path),
        filename="SecureVision_AI_Project_Report.md",
        media_type="text/markdown",
    )
