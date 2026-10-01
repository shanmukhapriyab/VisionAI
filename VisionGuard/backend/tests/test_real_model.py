"""End-to-end test with the REAL YOLO model on a real photo (skipped if not installed)."""
from pathlib import Path

import cv2
import pytest

pytest.importorskip("ultralytics")

from app.detector import YoloDetector          # noqa: E402
from app.pipeline import FramePipeline         # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "bus.jpg"


@pytest.fixture(scope="module")
def detector():
    d = YoloDetector()
    try:
        d.load()
    except Exception as e:                      # offline and no weights -> cannot run this test
        pytest.skip(f"model unavailable: {e}")
    return d


def test_real_model_finds_bus_and_people(detector):
    img = cv2.imread(str(FIXTURE))
    assert img is not None
    out = FramePipeline(detector).process(img, "real", conf=0.4, now=0.0)
    labels = {d["label"] for d in out["detections"]}
    assert "bus" in labels and "person" in labels
    for d in out["detections"]:
        assert d["position"] in ("left", "center", "right")
        assert 0.4 <= d["confidence"] <= 1.0
        assert d["danger"]["level"] in ("SAFE", "CAUTION", "WARNING", "DANGER")
    assert out["timing"]["inference_ms"] > 0


def test_blank_image_yields_no_detections(detector):
    import numpy as np
    out = FramePipeline(detector).process(np.zeros((480, 640, 3), np.uint8), "blank", now=0.0)
    assert out["detections"] == []
