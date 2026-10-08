"""Train flood-risk classifier and vulnerability regressor with honest validation."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_training.features import FEATURE_COLUMNS, LABEL_ORDER, add_engineered_features
from src.paths import CLASSIFIER_PATH, FLOOD_CSV, METRICS_JSON, MODELS_DIR, REGRESSOR_PATH

warnings.filterwarnings("ignore", category=UserWarning)


def _try_xgboost():
    try:
        from xgboost import XGBClassifier, XGBRegressor

        return XGBClassifier, XGBRegressor
    except Exception:
        return None, None


def _try_smote(X, y, random_state=42):
    try:
        from imblearn.over_sampling import SMOTE

        counts = pd.Series(y).value_counts()
        if counts.min() < 6:
            return X, y, False
        sampler = SMOTE(random_state=random_state)
        X_res, y_res = sampler.fit_resample(X, y)
        return X_res, y_res, True
    except Exception:
        return X, y, False


def _clf_metrics(y_true, y_pred) -> dict:
    labels = LABEL_ORDER
    rec = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    rec_map = {lab: float(r) for lab, r in zip(labels, rec)}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "high_risk_recall": rec_map.get("High", 0.0),
        "per_class_recall": rec_map,
        "classification_report": classification_report(
            y_true, y_pred, labels=labels, zero_division=0
        ),
    }


def train():
    df = pd.read_csv(FLOOD_CSV, parse_dates=["date"])
    df = add_engineered_features(df)
    df = df.dropna(subset=FEATURE_COLUMNS + ["flood_risk", "flood_risk_score"])

    X = df[FEATURE_COLUMNS]
    y = df["flood_risk"].astype(str)
    y_reg = df["flood_risk_score"].astype(float)

    temporal_train = df["date"] < "2023-01-01"
    temporal_test = df["date"] >= "2023-01-01"

    locations = df[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)
    holdout = locations.sample(n=min(3, len(locations)), random_state=7)
    holdout_keys = set(zip(holdout.latitude.round(5), holdout.longitude.round(5)))
    loc_key = list(zip(df.latitude.round(5), df.longitude.round(5)))
    spatial_test_mask = np.array([k in holdout_keys for k in loc_key])

    XGBClassifier, XGBRegressor = _try_xgboost()

    candidates = {
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000, class_weight="balanced"
                    ),
                ),
            ]
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=180,
            max_depth=12,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        ),
    }
    if XGBClassifier is not None:
        candidates["XGBoost"] = XGBClassifier(
            n_estimators=180,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            n_jobs=-1,
            random_state=42,
            eval_metric="mlogloss",
        )

    label_to_idx = {lab: i for i, lab in enumerate(LABEL_ORDER)}
    idx_to_label = {i: lab for lab, i in label_to_idx.items()}

    results = {}
    best_name = None
    best_score = -1
    best_model = None

    X_tr = X[temporal_train]
    y_tr = y[temporal_train]
    X_te = X[temporal_test]
    y_te = y[temporal_test]
    X_tr_s, y_tr_s, smote_used = _try_smote(X_tr, y_tr)

    for name, model in candidates.items():
        y_fit = y_tr_s
        y_eval_true = y_te
        if name == "XGBoost":
            y_fit = np.array([label_to_idx[v] for v in y_tr_s])
        model.fit(X_tr_s, y_fit)
        pred = model.predict(X_te)
        if name == "XGBoost":
            pred = np.array([idx_to_label[int(v)] for v in pred])
        metrics = _clf_metrics(y_eval_true, pred)
        results[name] = metrics
        score = 0.6 * metrics["macro_f1"] + 0.4 * metrics["high_risk_recall"]
        if score > best_score:
            best_score = score
            best_name = name
            best_model = model

    # Spatial generalisation of the selected architecture (retrained on non-holdout years)
    spatial_train_mask = ~spatial_test_mask
    spatial_model = candidates[best_name]
    # refit a fresh clone
    from sklearn.base import clone

    spatial_clone = clone(spatial_model)
    y_sp = y[spatial_train_mask]
    X_sp = X[spatial_train_mask]
    if best_name == "XGBoost":
        spatial_clone.fit(X_sp, np.array([label_to_idx[v] for v in y_sp]))
        sp_pred = np.array([idx_to_label[int(v)] for v in spatial_clone.predict(X[spatial_test_mask])])
    else:
        spatial_clone.fit(X_sp, y_sp)
        sp_pred = spatial_clone.predict(X[spatial_test_mask])
    spatial_metrics = _clf_metrics(y[spatial_test_mask], sp_pred)

    # Final classifier: all data (dashboard inference). Metrics above remain the honest hold-outs.
    final_clf = clone(spatial_model)
    if best_name == "XGBoost":
        final_clf.fit(X, np.array([label_to_idx[v] for v in y]))
    else:
        final_clf.fit(X, y)

    # Regression
    reg_candidates = {
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=180, max_depth=12, n_jobs=-1, random_state=42
        )
    }
    if XGBRegressor is not None:
        reg_candidates["XGBoostRegressor"] = XGBRegressor(
            n_estimators=180,
            max_depth=6,
            learning_rate=0.08,
            n_jobs=-1,
            random_state=42,
        )

    best_reg_name = None
    best_rmse = 1e18
    best_reg = None
    reg_results = {}
    for name, model in reg_candidates.items():
        model.fit(X[temporal_train], y_reg[temporal_train])
        pred = model.predict(X[temporal_test])
        rmse = float(np.sqrt(mean_squared_error(y_reg[temporal_test], pred)))
        mae = float(mean_absolute_error(y_reg[temporal_test], pred))
        reg_results[name] = {"rmse": rmse, "mae": mae}
        if rmse < best_rmse:
            best_rmse = rmse
            best_reg_name = name
            best_reg = model

    final_reg = clone(best_reg)
    final_reg.fit(X, y_reg)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    classifier_bundle = {
        "model": final_clf,
        "feature_columns": FEATURE_COLUMNS,
        "label_order": LABEL_ORDER,
        "model_name": best_name,
        "uses_int_labels": best_name == "XGBoost",
    }
    regressor_bundle = {
        "model": final_reg,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": best_reg_name,
    }
    joblib.dump(classifier_bundle, CLASSIFIER_PATH)
    joblib.dump(regressor_bundle, REGRESSOR_PATH)

    payload = {
        "notes": [
            "Labels are rule-based (rainfall/elevation/drainage), not surveyed flood extents.",
            "Engineered features (rolling rainfall, monsoon flag, interaction) are added so the model is not a pure re-derivation of the formula.",
            "Headline selection uses Macro-F1 and High-risk recall, not accuracy.",
            "Do not interpret these scores as operational flood-certainty.",
        ],
        "n_rows": int(len(df)),
        "class_balance": y.value_counts().to_dict(),
        "smote_on_temporal_train": smote_used,
        "best_classifier": best_name,
        "temporal_split": {
            "train": "2019-01-01 to 2022-12-31",
            "test": "2023-01-01 to 2023-12-31",
            "models": results,
        },
        "spatial_split": {
            "held_out_locations": holdout.to_dict(orient="records"),
            "metrics": spatial_metrics,
            "model_architecture": best_name,
        },
        "best_regressor": best_reg_name,
        "regression_temporal": reg_results,
        "feature_columns": FEATURE_COLUMNS,
    }
    # classification_report strings are large; keep them
    METRICS_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("best_classifier", "best_regressor", "class_balance")}, indent=2))
    print("Temporal Macro-F1 by model:")
    for name, m in results.items():
        print(f"  {name}: macro_f1={m['macro_f1']:.3f} high_recall={m['high_risk_recall']:.3f} acc={m['accuracy']:.3f}")
    print(f"Saved {CLASSIFIER_PATH} and {REGRESSOR_PATH}")


if __name__ == "__main__":
    train()
