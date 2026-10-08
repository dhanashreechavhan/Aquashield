from __future__ import annotations

from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from src.model_training.features import FEATURE_COLUMNS, LABEL_ORDER, features_from_manual
from src.paths import CLASSIFIER_PATH, REGRESSOR_PATH


@lru_cache(maxsize=1)
def load_classifier():
    if not CLASSIFIER_PATH.exists():
        return None
    return joblib.load(CLASSIFIER_PATH)


@lru_cache(maxsize=1)
def load_regressor():
    if not REGRESSOR_PATH.exists():
        return None
    return joblib.load(REGRESSOR_PATH)


def _vector(feature_dict: dict) -> pd.DataFrame:
    return pd.DataFrame([{col: feature_dict[col] for col in FEATURE_COLUMNS}])


def predict_flood_risk(feature_dict: dict) -> dict:
    clf_bundle = load_classifier()
    reg_bundle = load_regressor()
    if clf_bundle is None:
        return {"error": "Classifier not trained. Run src/model_training/train_flood_risk_model.py"}

    X = _vector(feature_dict)
    model = clf_bundle["model"]
    uses_int = clf_bundle.get("uses_int_labels", False)
    raw = model.predict(X)[0]
    if uses_int:
        label = LABEL_ORDER[int(raw)]
    else:
        label = str(raw)

    probabilities = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        classes = getattr(model, "classes_", None)
        if uses_int or (classes is not None and np.issubdtype(np.array(classes).dtype, np.integer)):
            probabilities = {LABEL_ORDER[int(c)]: float(p) for c, p in zip(classes, proba)}
        else:
            probabilities = {str(c): float(p) for c, p in zip(classes, proba)}

    score = None
    if reg_bundle is not None:
        score = float(np.clip(reg_bundle["model"].predict(X)[0], 0, 100))

    return {
        "label": label,
        "vulnerability_score": score,
        "probabilities": probabilities,
        "model_name": clf_bundle.get("model_name"),
        "features": feature_dict,
    }


def predict_from_manual(**kwargs) -> dict:
    return predict_flood_risk(features_from_manual(**kwargs))
