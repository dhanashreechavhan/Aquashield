from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = ROOT / "config.yaml"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_SYNTHETIC = ROOT / "data" / "synthetic"
DATA_COMMUNITY = ROOT / "data" / "community"
UPLOADS = DATA_COMMUNITY / "uploads"
MODELS_DIR = ROOT / "models"

FLOOD_CSV = DATA_PROCESSED / "flood_risk_dataset.csv"
ROAD_CSV = DATA_PROCESSED / "road_risk_dataset.csv"
EVENTS_CSV = DATA_RAW / "known_flood_events.csv"
FORECAST_CSV = DATA_RAW / "live_forecast.csv"
METRICS_JSON = MODELS_DIR / "metrics.json"
CLASSIFIER_PATH = MODELS_DIR / "best_classifier.joblib"
REGRESSOR_PATH = MODELS_DIR / "best_regressor.joblib"
COMMUNITY_DB = DATA_COMMUNITY / "reports.sqlite"
SOCIAL_DIR = ROOT / "data" / "social"
SOCIAL_REPORTS = SOCIAL_DIR / "flood_reports.json"

VVN_CENTER = (19.40, 72.83)

NAMED_PLACES = {
    "Vasai West": (19.361, 72.805),
    "Vasai East": (19.381, 72.835),
    "Nalasopara West": (19.418, 72.811),
    "Nalasopara East": (19.427, 72.848),
    "Virar West": (19.455, 72.808),
    "Virar East": (19.456, 72.842),
    "Naigaon": (19.351, 72.846),
    "Pelhar": (19.448, 72.862),
    "Global Vipassana Pagoda area": (19.381, 72.813),
}
