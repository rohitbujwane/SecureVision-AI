"""
Data preprocessing service.
Handles feature selection, missing value treatment, scaling, and transformations.
"""

import numpy as np
import pandas as pd
import joblib
from typing import Tuple, List, Optional
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from backend.config import SUPPORTED_FEATURES, SCALER_ARTIFACT_PATH


def select_features(df: pd.DataFrame, feature_list: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    Select supported numeric features from the DataFrame.
    
    Args:
        df: Input DataFrame
        feature_list: Optional specific feature list; defaults to SUPPORTED_FEATURES
    
    Returns:
        Tuple of (feature DataFrame, list of selected feature names)
    """
    if feature_list is None:
        feature_list = SUPPORTED_FEATURES

    available = [f for f in feature_list if f in df.columns]
    feature_df = df[available].copy()

    # Ensure all columns are numeric
    for col in available:
        feature_df[col] = pd.to_numeric(feature_df[col], errors='coerce')

    return feature_df, available


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing, infinite, and invalid values in feature columns.
    Strategy: Replace inf with NaN, then fill NaN with column median.
    """
    df = df.copy()
    # Replace inf/-inf with NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Fill NaN with column median (robust to outliers)
    for col in df.columns:
        median_val = df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        df[col].fillna(median_val, inplace=True)

    return df


def fit_scaler(df: pd.DataFrame, save_artifact: bool = False) -> StandardScaler:
    """
    Fit a StandardScaler on training data.
    Only saves to disk if save_artifact is explicitly True.
    """
    scaler = StandardScaler()
    scaler.fit(df)
    if save_artifact:
        save_scaler(scaler)
    return scaler


def save_scaler(scaler: StandardScaler, path: Optional[Path] = None) -> None:
    """
    Explicitly persist a fitted StandardScaler artifact to disk.
    """
    target_path = path or SCALER_ARTIFACT_PATH
    joblib.dump(scaler, target_path)


def load_scaler(path: Optional[Path] = None) -> Optional[StandardScaler]:
    """
    Load a previously fitted scaler from disk.
    """
    target_path = path or SCALER_ARTIFACT_PATH
    if target_path.exists():
        try:
            scaler = joblib.load(target_path)
            if isinstance(scaler, StandardScaler):
                return scaler
        except Exception:
            pass
    return None


def transform_features(df: pd.DataFrame, scaler: Optional[StandardScaler] = None,
                       fit: bool = False,
                       save_scaler_artifact: bool = False) -> Tuple[np.ndarray, StandardScaler]:
    """
    Apply StandardScaler transformation to features.
    
    Args:
        df: Feature DataFrame (cleaned)
        scaler: Pre-fitted scaler (for inference)
        fit: If True, fit a new scaler on this data (for training)
        save_scaler_artifact: If True and fit=True, persist scaler to disk
    
    Returns:
        Tuple of (scaled numpy array, scaler used)
    """
    if fit:
        scaler = fit_scaler(df, save_artifact=save_scaler_artifact)
        scaled = scaler.transform(df)
    elif scaler is not None:
        scaled = scaler.transform(df)
    else:
        # Fallback: fit on inference data (in-memory only, never saved)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(df)

    return scaled, scaler


def preprocess_pipeline(df: pd.DataFrame, feature_list: Optional[List[str]] = None,
                        scaler: Optional[StandardScaler] = None,
                        fit: bool = False,
                        save_scaler_artifact: bool = False) -> Tuple[np.ndarray, List[str], StandardScaler, pd.DataFrame]:
    """
    Full preprocessing pipeline: select features → handle missing → scale.
    
    Args:
        df: Input DataFrame with all columns
        feature_list: Features to select
        scaler: Pre-fitted scaler for inference
        fit: Whether to fit new scaler (training mode)
        save_scaler_artifact: Whether to persist fitted scaler to disk
    
    Returns:
        Tuple of (scaled array, feature names, scaler, cleaned feature DataFrame)
    """
    feature_df, used_features = select_features(df, feature_list)
    cleaned_df = handle_missing_values(feature_df)
    scaled_data, scaler = transform_features(
        cleaned_df, scaler=scaler, fit=fit, save_scaler_artifact=save_scaler_artifact
    )

    return scaled_data, used_features, scaler, cleaned_df

