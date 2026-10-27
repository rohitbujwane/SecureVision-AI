"""
Model evaluation script.
Evaluates model on held-out data using an isolated evaluation pipeline.
Guarantees that production artifacts in models/ are NEVER overwritten.

Usage:
    python scripts/evaluate_model.py [--data path/to/data.csv] [--split auto|chronological|random] [--test-size 0.3] [--val-size 0.0] [--contamination 0.1]
"""

import sys
import json
import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
from backend.services.parser import parse_csv
from backend.services.evaluation import run_evaluation_pipeline
from backend.database import init_db, get_db_session, ExperimentResult
from backend.config import DATA_DIR, RESEARCH_DIR, MODEL_CONTAMINATION, MODEL_N_ESTIMATORS, MODEL_RANDOM_STATE


def main():
    parser = argparse.ArgumentParser(description="Evaluate the anomaly detection model.")
    parser.add_argument(
        "--data", type=str,
        default=str(DATA_DIR / "sample_logs.csv"),
        help="Path to labeled evaluation data."
    )
    parser.add_argument(
        "--test-size", type=float, default=0.3,
        help="Fraction of data to hold out for testing."
    )
    parser.add_argument(
        "--val-size", type=float, default=0.0,
        help="Fraction of data reserved for validation (contamination tuning)."
    )
    parser.add_argument(
        "--split", type=str, default="auto", choices=["auto", "chronological", "random"],
        help="Data partitioning strategy ('auto' selects chronological if timestamps exist)."
    )
    parser.add_argument(
        "--contamination", type=float, default=MODEL_CONTAMINATION,
        help="Contamination parameter for Isolation Forest."
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[ERROR] Data file not found: {data_path}")
        sys.exit(1)

    # Initialize database
    init_db()

    # Load and parse data
    print(f"[INFO] Loading data from: {data_path}")
    with open(data_path, 'rb') as f:
        content = f.read()

    df, parse_info = parse_csv(content)
    print(f"[INFO] Parsed {parse_info['total_rows']} rows, {parse_info['feature_count']} features")

    if not parse_info['has_label']:
        print("[WARNING] No label column found. Supervised evaluation cannot be performed.")
        return

    exp_name = f"eval_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    print(f"[INFO] Running isolated evaluation pipeline (split={args.split}, test_size={args.test_size}, val_size={args.val_size}, contamination={args.contamination})...")
    metrics = run_evaluation_pipeline(
        df=df,
        dataset_name=data_path.name,
        test_size=args.test_size,
        val_size=args.val_size,
        split_strategy=args.split,
        contamination=args.contamination,
        n_estimators=MODEL_N_ESTIMATORS,
        random_state=MODEL_RANDOM_STATE,
        experiment_name=exp_name,
    )

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS (HELD-OUT TEST PARTITION)")
    print("=" * 60)
    print(f"  Protocol: {metrics.get('evaluation_protocol', 'N/A')}")
    print(f"  Total test samples evaluated: {metrics['total_samples']}")
    print(f"  Accuracy:             {metrics.get('accuracy_percent', 0.0):.2f}% ({metrics.get('accuracy', 0.0):.4f})")
    print(f"  Precision:            {metrics.get('precision_percent', 0.0):.2f}% ({metrics.get('precision', 0.0):.4f})")
    print(f"  Recall (Detection):   {metrics.get('recall_percent', 0.0):.2f}% ({metrics.get('recall', 0.0):.4f})")
    print(f"  F1 Score:             {metrics.get('f1_percent', 0.0):.2f}% ({metrics.get('f1', 0.0):.4f})")
    print(f"  Specificity:          {metrics.get('specificity_percent', 0.0):.2f}% ({metrics.get('specificity', 0.0):.4f})")
    print(f"  False Positive Rate:  {metrics.get('false_positive_rate_percent', 0.0):.2f}% ({metrics.get('false_positive_rate', 0.0):.4f})")
    print(f"  False Negative Rate:  {metrics.get('false_negative_rate_percent', 0.0):.2f}% ({metrics.get('false_negative_rate', 0.0):.4f})")
    print(f"  Anomaly Prevalence:   {metrics.get('ground_truth_prevalence_percent', 0.0):.2f}% (true: {metrics.get('ground_truth_anomalies_count', 0)})")
    print(f"  Predicted Anom Rate:  {metrics.get('predicted_anomaly_rate_percent', 0.0):.2f}% (flagged: {metrics.get('predicted_anomalies_count', 0)})")
    print(f"  Confusion Matrix:     {metrics['confusion_matrix']}")
    print(f"  Class Distribution:   {metrics['class_distribution']}")
    print(f"  Threshold Config:     {metrics.get('threshold_configuration', {})}")
    if "baseline_comparison" in metrics:
        b = metrics["baseline_comparison"]
        print("-" * 60)
        print("BASELINE COMPARISON:")
        print(f"  All-Normal Baseline:  Acc={b['all_normal_baseline']['accuracy_percent']:.2f}%, Rec={b['all_normal_baseline']['recall_percent']:.2f}%, FPR={b['all_normal_baseline']['false_positive_rate_percent']:.2f}%")
        print(f"  Isolation Forest:     Acc={b['isolation_forest_model']['accuracy_percent']:.2f}%, Rec={b['isolation_forest_model']['recall_percent']:.2f}%, FPR={b['isolation_forest_model']['false_positive_rate_percent']:.2f}%")
        print(f"  Assessment: {b.get('trade_off_analysis', '')}")
    print("=" * 60)

    # Save results to database
    db = get_db_session()
    try:
        result = ExperimentResult(
            experiment_name=metrics["experiment_name"],
            model_type=metrics["model_type"],
            dataset_name=metrics["dataset_name"],
            total_samples=metrics["total_samples"],
            precision_score=metrics["precision"],
            recall_score=metrics["recall"],
            f1_score=metrics["f1"],
            false_positive_rate=metrics["false_positive_rate"],
            confusion_matrix=json.dumps(metrics["confusion_matrix"]),
            class_distribution=json.dumps(metrics["class_distribution"]),
            notes=json.dumps({
                "protocol": metrics.get("evaluation_protocol"),
                "split_strategy": metrics.get("split_strategy"),
                "split_ranges": metrics.get("split_ranges"),
                "threshold_configuration": metrics.get("threshold_configuration"),
                "session_leakage": metrics.get("session_leakage_analysis"),
            }),
        )
        db.add(result)
        db.commit()
        print("[INFO] Results saved to database.")
    except Exception as e:
        print(f"[WARNING] Failed to save to database: {e}")
    finally:
        db.close()

    # Save results to research directory
    results_dir = RESEARCH_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / f"evaluation_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[INFO] Results saved to: {results_file}")
    print("[SUCCESS] Production artifacts in models/ remain completely untouched.")


if __name__ == "__main__":
    main()
