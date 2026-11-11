import hashlib
import math
import joblib
import pandas as pd

from .schema import EXPECTED_FEATURES


def load_artifact(path):
    artifact = joblib.load(path)
    validate_artifact(artifact)
    version = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return artifact, version


def validate_artifact(artifact):
    required = {'pipeline', 'model_name', 'threshold', 'feature_columns', 'target'}
    if not isinstance(artifact, dict) or not required.issubset(artifact):
        raise ValueError('Saved model artifact is missing required metadata.')
    columns = artifact['feature_columns']
    if len(columns) != len(set(columns)) or set(columns) != set(EXPECTED_FEATURES):
        raise ValueError('Saved feature_columns do not match the versioned feature schema.')
    threshold = float(artifact['threshold'])
    if not math.isfinite(threshold) or not 0 <= threshold <= 1 or artifact['target'] != 'Shortlisted':
        raise ValueError('Saved model target or threshold is incompatible.')
    if 1 not in list(artifact['pipeline'].classes_):
        raise ValueError('Saved classifier has no positive class 1.')
    return artifact


def infer(records, artifact):
    if not records:
        return []
    frame = pd.DataFrame(records)
    absent = [c for c in artifact['feature_columns'] if c not in frame.columns]
    if absent:
        raise ValueError('Missing engineered model inputs: ' + ', '.join(absent))
    positive = list(artifact['pipeline'].classes_).index(1)
    probabilities = artifact['pipeline'].predict_proba(frame[artifact['feature_columns']])[:, positive]
    results = [float(p) for p in probabilities]
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in results):
        raise ValueError('Model returned a non-finite or out-of-range score.')
    return results
