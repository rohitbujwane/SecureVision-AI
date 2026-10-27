"""
Explanation generation service.
Produces human-readable reasons for anomaly flags and investigation recommendations.
Uses feature comparisons and transparent rules — not black-box outputs.
"""

import json
from typing import Dict, List, Any, Optional
import numpy as np


def generate_explanation(
    feature_values: Dict[str, float],
    anomaly_score: float,
    severity: str,
    feature_stats: Dict[str, Dict[str, float]],
    prediction: int,
) -> Dict[str, Any]:
    """
    Generate an explanation for why a record was flagged.
    
    Args:
        feature_values: The record's feature values
        anomaly_score: Model's anomaly score
        severity: Assigned severity level
        feature_stats: Training data statistics per feature
        prediction: 0=normal, 1=anomalous
    
    Returns:
        Explanation dict with reasons and contributing features
    """
    reasons = []
    contributing_features = []

    if prediction == 0:
        return {
            "summary": "This event appears normal based on the model's analysis.",
            "reasons": ["Feature values are within expected ranges."],
            "contributing_features": [],
            "anomaly_score_interpretation": f"Score: {anomaly_score:.4f} (higher = more normal)",
            "confidence_note": "Model-based assessment; manual review may still be warranted.",
        }

    # Analyze each feature for deviations
    for feat, value in feature_values.items():
        if feat not in feature_stats:
            continue

        stats = feature_stats[feat]
        mean = stats.get("mean", 0)
        std = stats.get("std", 1)
        q25 = stats.get("q25", 0)
        q75 = stats.get("q75", 0)
        min_val = stats.get("min", 0)
        max_val = stats.get("max", 0)
        iqr = q75 - q25

        if std == 0:
            continue

        z_score = abs(value - mean) / std if std > 0 else 0

        # Feature deviates significantly
        if z_score > 3:
            direction = "above" if value > mean else "below"
            reasons.append(
                f"'{feat}' is {z_score:.1f} standard deviations {direction} the training mean "
                f"(value: {value:.2f}, mean: {mean:.2f})"
            )
            contributing_features.append({
                "feature": feat,
                "value": round(value, 4),
                "mean": round(mean, 4),
                "z_score": round(z_score, 2),
                "deviation": direction,
            })
        elif z_score > 2:
            direction = "above" if value > mean else "below"
            reasons.append(
                f"'{feat}' shows a notable deviation ({z_score:.1f}σ {direction} mean, "
                f"value: {value:.2f})"
            )
            contributing_features.append({
                "feature": feat,
                "value": round(value, 4),
                "mean": round(mean, 4),
                "z_score": round(z_score, 2),
                "deviation": direction,
            })

        # Check IQR outlier
        if iqr > 0:
            if value > q75 + 1.5 * iqr or value < q25 - 1.5 * iqr:
                if not any(cf["feature"] == feat for cf in contributing_features):
                    reasons.append(
                        f"'{feat}' is an outlier (value: {value:.2f}, IQR range: [{q25:.2f}, {q75:.2f}])"
                    )
                    contributing_features.append({
                        "feature": feat,
                        "value": round(value, 4),
                        "iqr_low": round(q25, 4),
                        "iqr_high": round(q75, 4),
                        "deviation": "iqr_outlier",
                    })

    # If no specific deviations found but model flagged it
    if not reasons:
        reasons.append(
            "The combination of feature values deviates from normal patterns, "
            "even though individual features may appear within range."
        )

    # Build summary
    summary = _build_summary(severity, len(contributing_features), anomaly_score)

    return {
        "summary": summary,
        "reasons": reasons,
        "contributing_features": contributing_features,
        "anomaly_score_interpretation": _interpret_score(anomaly_score),
        "confidence_note": (
            "This assessment is based on statistical deviation from training data patterns. "
            "It does not confirm a security incident. Manual investigation is recommended."
        ),
    }


def generate_investigation_steps(
    severity: str,
    feature_values: Dict[str, float],
    contributing_features: List[Dict],
    source_ip: Optional[str] = None,
    dest_ip: Optional[str] = None,
    protocol: Optional[str] = None,
) -> List[str]:
    """
    Generate recommended investigation steps based on the alert context.
    """
    steps = []

    # General first steps
    steps.append("Review the full event record and its surrounding events in the original log source.")

    if source_ip:
        steps.append(f"Investigate source IP '{source_ip}' — check for other anomalous events from this address.")
    if dest_ip:
        steps.append(f"Verify destination IP '{dest_ip}' — check if this is a known internal or external endpoint.")
    if protocol:
        steps.append(f"Review protocol '{protocol}' usage patterns for this source and destination pair.")

    # Feature-specific steps
    for cf in contributing_features[:5]:  # Top 5 contributing features
        feat = cf.get("feature", "")
        if "packet" in feat.lower():
            steps.append(
                f"Examine packet metrics ('{feat}') — unusual packet sizes or counts may indicate "
                "data exfiltration, scanning, or flooding."
            )
        elif "duration" in feat.lower():
            steps.append(
                f"Check flow duration ('{feat}') — unusually long or short connections may indicate "
                "persistent backdoors or port scanning."
            )
        elif "bytes" in feat.lower():
            steps.append(
                f"Analyze byte transfer patterns ('{feat}') — significant deviations could suggest "
                "data theft or command-and-control traffic."
            )
        elif "iat" in feat.lower():
            steps.append(
                f"Review inter-arrival timing ('{feat}') — regular intervals may indicate "
                "automated/scripted behavior."
            )
        elif "flag" in feat.lower() or "syn" in feat.lower() or "rst" in feat.lower():
            steps.append(
                f"Inspect TCP flag counts ('{feat}') — abnormal flag patterns can indicate "
                "SYN floods, RST attacks, or other TCP-based exploits."
            )

    # Severity-specific steps
    if severity in ("critical", "high"):
        steps.append(
            "PRIORITY: Escalate to the security team for immediate triage. "
            "Document findings and preserve evidence."
        )
        steps.append("Check for correlated alerts in SIEM or IDS logs.")
    elif severity == "medium":
        steps.append("Add to the investigation queue for analyst review within the current shift.")
    else:
        steps.append("Log for trend analysis and close if no additional context is found.")

    steps.append(
        "Cross-reference with threat intelligence feeds and known IoCs if available."
    )

    return steps


def _build_summary(severity: str, num_contributing: int, score: float) -> str:
    """Build a human-readable summary sentence."""
    severity_labels = {
        "critical": "Critical anomaly detected",
        "high": "High-severity anomaly detected",
        "medium": "Moderate anomaly detected",
        "low": "Minor anomaly detected",
    }
    prefix = severity_labels.get(severity, "Anomaly detected")

    if num_contributing > 0:
        return (
            f"{prefix} — {num_contributing} feature(s) show significant deviation "
            f"from expected patterns (score: {score:.4f}). Requires investigation."
        )
    else:
        return (
            f"{prefix} — the overall feature pattern deviates from training data "
            f"(score: {score:.4f}). Requires investigation."
        )


def _interpret_score(score: float) -> str:
    """Provide a plain-language interpretation of the anomaly score."""
    if score <= -0.35:
        return f"Score: {score:.4f} — Extremely unusual, far from normal cluster."
    elif score <= -0.25:
        return f"Score: {score:.4f} — Highly unusual behavior observed."
    elif score <= -0.15:
        return f"Score: {score:.4f} — Moderately unusual, some features deviate."
    elif score <= 0:
        return f"Score: {score:.4f} — Mildly unusual, near decision boundary."
    else:
        return f"Score: {score:.4f} — Within normal range."
