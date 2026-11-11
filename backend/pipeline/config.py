from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / 'fresher_recruitment_model.joblib'
REFERENCE_PATH = ROOT / 'AI_Fresher_Recruitment_ML_Dataset.csv'
FEATURE_VERSION = 'incepta-features-v1'
SCORE_VERSION = 'incepta-weighted-v1'
MAXIMA = {'Project_Count': 5.0, 'Internship_Count': 4.0, 'Certification_Count': 5.0, 'Achievement_Count': 4.0}


@dataclass(frozen=True)
class PipelineConfig:
    model_path: Path = MODEL_PATH
    reference_path: Path = REFERENCE_PATH
    legacy_penalties: bool = False
