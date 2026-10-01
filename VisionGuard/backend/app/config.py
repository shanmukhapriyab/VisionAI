"""Central configuration. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

# Lightweight pretrained COCO model (nano, ~6 MB, runs on CPU).
MODEL_NAME = os.getenv("VISIONGUARD_MODEL", "yolov8n.pt")
MODEL_URL = os.getenv(
    "VISIONGUARD_MODEL_URL",
    "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt",
)
# Smaller = faster. 320 is fastest, 416 is a good CPU balance, 640 is most accurate.
IMG_SIZE = int(os.getenv("VISIONGUARD_IMGSZ", "416"))
DEFAULT_CONFIDENCE = float(os.getenv("VISIONGUARD_CONF", "0.40"))
MAX_DETECTIONS = 30

# Distance estimation assumes a typical phone/laptop camera horizontal field of view.
CAMERA_HFOV_DEG = float(os.getenv("VISIONGUARD_HFOV", "65"))

DB_PATH = Path(os.getenv("VISIONGUARD_DB", str(DATA_DIR / "visionguard.db")))
MAX_FRAME_BYTES = 6 * 1024 * 1024
HISTORY_MIN_INTERVAL_S = 5.0
HISTORY_MAX_ROWS = 5000

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "VISIONGUARD_CORS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]
