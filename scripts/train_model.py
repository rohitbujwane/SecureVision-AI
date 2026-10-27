"""
Model training script.
Trains an Isolation Forest model on the provided dataset.
Saves model artifact, scaler, and metadata.

Usage:
    python scripts/train_model.py [--data path/to/data.csv]
"""

import sys
import argparse
from pathlib import Path

# Setup path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from backend.services.parser import parse_csv
from backend.services.detector import AnomalyDetector
from backend.config import DATA_DIR


def main():
    parser = argparse.ArgumentParser(description="Train the anomaly detection model.")
    parser.add_argument(
        "--data",
        type=str,
        default=str(DATA_DIR / "sample_logs.csv"),
        help="Path to training CSV file."
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[ERROR] Data file not found: {data_path}")
        print("Run `python scripts/generate_dataset.py` first to create sample data.")
        sys.exit(1)

    print(f"[INFO] Loading data from: {data_path}")
    with open(data_path, 'rb') as f:
        content = f.read()

    df, parse_info = parse_csv(content)
    print(f"[INFO] Parsed {parse_info['total_rows']} rows, "
          f"{parse_info['feature_count']} features available")
    print(f"[INFO] Features: {parse_info['available_features']}")

    if parse_info['has_label']:
        print(f"[INFO] Label distribution: {parse_info['label_distribution']}")

    # Train model
    det = AnomalyDetector()
    print("[INFO] Training Isolation Forest model...")
    metadata = det.train(df, dataset_name=data_path.name)

    print(f"[SUCCESS] Model trained!")
    print(f"  Version: {metadata['version']}")
    print(f"  Samples: {metadata['training_samples']}")
    print(f"  Features: {metadata['features']}")
    print(f"  Contamination: {metadata['contamination']}")

    # Quick validation
    predictions, scores, features = det.predict(df)
    n_anomalies = int(predictions.sum())
    print(f"\n[VALIDATION] On training data:")
    print(f"  Total: {len(predictions)}")
    print(f"  Anomalies: {n_anomalies} ({n_anomalies/len(predictions)*100:.1f}%)")
    print(f"  Normal: {len(predictions) - n_anomalies}")


if __name__ == "__main__":
    main()
