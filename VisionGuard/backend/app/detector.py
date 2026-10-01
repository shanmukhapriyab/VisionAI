"""YOLO detector wrapper (Ultralytics YOLOv8-nano, CPU).

This module never invents detections. If the model cannot be loaded or inference
fails, a DetectorError is raised and the API reports a real error to the UI.
"""
import logging
import os
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import config
from .objects import CATALOG

log = logging.getLogger("visionguard.detector")


class DetectorError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RawDetection:
    label: str
    confidence: float
    box: tuple  # (x1, y1, x2, y2) pixels in the submitted frame


class YoloDetector:
    def __init__(self, model_path: Path | None = None, imgsz: int = config.IMG_SIZE,
                 auto_download: bool = True):
        self.model_path = Path(model_path) if model_path else config.MODEL_DIR / config.MODEL_NAME
        self.imgsz = imgsz
        self.auto_download = auto_download
        self.state = "idle"          # idle | loading | ready | error
        self.error: dict | None = None
        self._model = None
        self._class_ids: list[int] = []
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    # ---- lifecycle -------------------------------------------------------
    def start_background_load(self):
        if self.state in ("loading", "ready"):
            return
        self.state = "loading"
        threading.Thread(target=self._safe_load, daemon=True, name="model-loader").start()

    def _safe_load(self):
        try:
            self.load()
        except DetectorError as e:
            log.error("Model load failed [%s]: %s", e.code, e.message)

    def load(self):
        with self._load_lock:
            if self.state == "ready":
                return
            self.state, self.error = "loading", None
            try:
                try:
                    from ultralytics import YOLO
                except Exception as e:  # ImportError or a broken torch install
                    raise DetectorError(
                        "ULTRALYTICS_MISSING",
                        "The 'ultralytics' package could not be imported "
                        f"({type(e).__name__}: {e}). Run: pip install -r requirements.txt",
                    )
                self._ensure_weights()
                try:
                    model = YOLO(str(self.model_path))
                    import numpy as np
                    model.predict(np.zeros((self.imgsz, self.imgsz, 3), np.uint8),
                                  imgsz=self.imgsz, device="cpu", verbose=False)  # warm-up
                except DetectorError:
                    raise
                except Exception as e:
                    raise DetectorError(
                        "MODEL_LOAD_FAILED",
                        f"YOLO model '{self.model_path.name}' failed to load: {e}. "
                        "Delete the file in backend/models and restart to download it again.",
                    )
                names = model.names if isinstance(model.names, dict) else dict(enumerate(model.names))
                self._class_ids = sorted(i for i, n in names.items() if n in CATALOG)
                if not self._class_ids:
                    raise DetectorError("MODEL_CLASSES", "The model contains none of the supported classes.")
                self._model = model
                self._names = names
                self.state = "ready"
                log.info("YOLO model ready: %s (%d classes tracked)", self.model_path.name, len(self._class_ids))
            except DetectorError as e:
                self.state = "error"
                self.error = {"code": e.code, "message": e.message}
                raise

    def _ensure_weights(self):
        if self.model_path.exists() and self.model_path.stat().st_size > 1_000_000:
            return
        if not self.auto_download:
            raise DetectorError("MODEL_MISSING", f"Model file not found: {self.model_path}")
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.model_path.with_suffix(".part")
        log.info("Downloading %s ...", config.MODEL_URL)
        try:
            with urllib.request.urlopen(config.MODEL_URL, timeout=60) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            os.replace(tmp, self.model_path)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            raise DetectorError(
                "MODEL_DOWNLOAD_FAILED",
                f"Could not download the YOLO model ({e}). Connect to the internet once, or download "
                f"yolov8n.pt manually from {config.MODEL_URL} and place it in {self.model_path.parent}.",
            )

    # ---- inference -------------------------------------------------------
    def status(self) -> dict:
        return {"state": self.state, "error": self.error, "model": self.model_path.name,
                "imgsz": self.imgsz, "device": "cpu"}

    def detect(self, image_bgr, conf: float = config.DEFAULT_CONFIDENCE) -> list[RawDetection]:
        if self.state != "ready" or self._model is None:
            if self.state == "error":
                raise DetectorError(self.error["code"], self.error["message"])
            raise DetectorError("MODEL_LOADING", "The AI model is still loading. Please wait a moment.")
        try:
            with self._infer_lock:
                results = self._model.predict(
                    image_bgr, imgsz=self.imgsz, conf=conf, classes=self._class_ids,
                    device="cpu", verbose=False, max_det=config.MAX_DETECTIONS,
                )
            boxes = results[0].boxes
            out = []
            for xyxy, c, k in zip(boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), boxes.cls.cpu().numpy()):
                out.append(RawDetection(self._names[int(k)], float(c), tuple(float(v) for v in xyxy)))
            return out
        except DetectorError:
            raise
        except Exception as e:
            log.exception("Inference failed")
            raise DetectorError("INFERENCE_FAILED", f"Detection failed: {e}")
