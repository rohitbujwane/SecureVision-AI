"""
CSV parser service.
Handles file validation, column mapping, and data extraction.
"""

import io
import csv
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional, Any
from backend.config import (
    MAX_UPLOAD_SIZE_BYTES, MAX_ROW_COUNT, COLUMN_NAME_MAP,
    SUPPORTED_FEATURES, MIN_REQUIRED_FEATURES
)


class ParseError(Exception):
    """Raised when CSV parsing fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def validate_file_size(content: bytes) -> None:
    """Check file size is within limits."""
    if len(content) == 0:
        raise ParseError("Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ParseError(
            f"File exceeds maximum size of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
        )


def detect_delimiter(sample: str) -> str:
    """Detect the most likely delimiter."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except csv.Error:
        return ','


def normalize_column_names(columns: List[str]) -> Dict[str, str]:
    """
    Map raw column names to canonical feature names.
    Returns a dict mapping original_name -> canonical_name.
    """
    mapping = {}
    for col in columns:
        normalized = col.strip().lower().replace('-', '_').replace('/', '_per_')
        # Try direct mapping
        if normalized in COLUMN_NAME_MAP:
            mapping[col] = COLUMN_NAME_MAP[normalized]
        # Try with spaces replaced by underscores
        elif normalized.replace(' ', '_') in COLUMN_NAME_MAP:
            mapping[col] = COLUMN_NAME_MAP[normalized.replace(' ', '_')]
        else:
            # Keep original with cleanup
            mapping[col] = normalized.replace(' ', '_')
    return mapping


def parse_csv(content: bytes) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse and validate a CSV file from raw bytes.
    
    Returns:
        Tuple of (DataFrame with normalized columns, parse info dict)
    
    Raises:
        ParseError on validation failure
    """
    # 1. Validate file size
    validate_file_size(content)

    # 2. Decode
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = content.decode('latin-1')
        except UnicodeDecodeError:
            raise ParseError("File encoding not supported. Please use UTF-8 or Latin-1.")

    if not text.strip():
        raise ParseError("File contains no data after decoding.")

    # 3. Detect delimiter
    sample = text[:4096]
    delimiter = detect_delimiter(sample)

    # 4. Read CSV
    try:
        df = pd.read_csv(io.StringIO(text), delimiter=delimiter, low_memory=False)
    except pd.errors.EmptyDataError:
        raise ParseError("CSV file is empty or contains only headers.")
    except pd.errors.ParserError as e:
        raise ParseError(f"Malformed CSV: {str(e)[:200]}")
    except Exception as e:
        raise ParseError(f"Failed to parse CSV: {str(e)[:200]}")

    # 5. Validate row count
    if len(df) == 0:
        raise ParseError("CSV contains headers but no data rows.")
    if len(df) > MAX_ROW_COUNT:
        raise ParseError(
            f"CSV contains {len(df)} rows, exceeding the limit of {MAX_ROW_COUNT}."
        )

    # 6. Normalize column names
    col_map = normalize_column_names(df.columns.tolist())
    df = df.rename(columns=col_map)

    # 7. Remove full duplicate rows
    original_count = len(df)
    df = df.drop_duplicates()
    duplicates_removed = original_count - len(df)

    # 8. Identify supported features present
    available_features = [f for f in SUPPORTED_FEATURES if f in df.columns]
    if len(available_features) < MIN_REQUIRED_FEATURES:
        raise ParseError(
            f"Insufficient supported features. Found {len(available_features)} "
            f"({', '.join(available_features) if available_features else 'none'}), "
            f"but at least {MIN_REQUIRED_FEATURES} are required.",
            details={
                "found_features": available_features,
                "supported_features": SUPPORTED_FEATURES,
                "columns_in_file": df.columns.tolist(),
            }
        )

    # 9. Extract metadata
    has_label = "label" in df.columns
    has_timestamp = "timestamp" in df.columns
    label_distribution = {}
    if has_label:
        label_distribution = df["label"].value_counts().to_dict()
        # Convert keys to strings for JSON serialization
        label_distribution = {str(k): int(v) for k, v in label_distribution.items()}

    # 10. Extract optional context columns
    context_columns = {}
    for col_name in ["source_ip", "src_ip", "destination_ip", "dst_ip", "dest_ip",
                     "protocol", "src_port", "dst_port", "source_port", "destination_port"]:
        if col_name in df.columns:
            context_columns[col_name] = True

    parse_info = {
        "total_rows": len(df),
        "original_rows": original_count,
        "duplicates_removed": duplicates_removed,
        "total_columns": len(df.columns),
        "available_features": available_features,
        "feature_count": len(available_features),
        "has_label": has_label,
        "has_timestamp": has_timestamp,
        "label_distribution": label_distribution,
        "context_columns": list(context_columns.keys()),
        "column_names": df.columns.tolist(),
    }

    return df, parse_info


def get_preview(df: pd.DataFrame, n_rows: int = 10) -> List[Dict]:
    """Get a preview of the first n rows as a list of dicts."""
    preview_df = df.head(n_rows).copy()
    # Replace NaN with None for JSON serialization
    preview_df = preview_df.where(preview_df.notna(), None)
    return preview_df.to_dict(orient="records")
