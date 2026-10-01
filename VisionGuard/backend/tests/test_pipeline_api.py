"""Pipeline + API plumbing tests.

A StubDetector feeds *known* boxes into the real pipeline/DB/API code so the logic
around the model can be verified. It is used ONLY in tests - the running app always
uses the real YOLO detector and reports errors instead of fabricating results.
"""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.detector import DetectorError, RawDetection
from app.main import create_app
from app.pipeline import FramePipeline


class StubDetector:
    def __init__(self, dets=None, state="ready", error=None):
        self.dets, self.state, self.error = dets or [], state, error

    def status(self):
        return {"state": self.state, "error": self.error, "model": "stub", "imgsz": 0, "device": "cpu"}

    def detect(self, image, conf=0.4):
        if self.state == "error":
            raise DetectorError(self.error["code"], self.error["message"])
        if self.state != "ready":
            raise DetectorError("MODEL_LOADING", "loading")
        return self.dets


def jpeg(w=640, h=480):
    ok, buf = cv2.imencode(".jpg", np.full((h, w, 3), 127, np.uint8))
    return buf.tobytes()


PERSON_CENTER = RawDetection("person", 0.9, (280, 150, 360, 400))     # ~3 m ahead
CHAIR_LEFT = RawDetection("chair", 0.8, (20, 200, 100, 380))


def test_pipeline_output_shape_and_priority():
    p = FramePipeline(StubDetector([CHAIR_LEFT, PERSON_CENTER]))
    out = p.process(np.zeros((480, 640, 3), np.uint8), "s1", now=0.0)
    assert out["summary"]["count"] == 2
    d = out["detections"]
    assert d[0]["label"] == "person" and d[0]["position"] == "center"
    assert d[1]["position"] == "left"
    for key in ("confidence", "distance_m", "danger", "message", "box", "alert_key"):
        assert key in d[0]
    assert 0 <= d[0]["box"]["x1"] < d[0]["box"]["x2"] <= 1
    assert out["summary"]["message"] == d[0]["message"]


def test_pipeline_empty_frame_is_safe_and_has_no_message():
    out = FramePipeline(StubDetector([])).process(np.zeros((480, 640, 3), np.uint8))
    assert out["detections"] == [] and out["summary"]["level"] == "SAFE" and out["summary"]["message"] is None


def test_pipeline_detects_approach_over_frames():
    growing = [RawDetection("car", 0.9, (250 - i * 6, 200 - i * 6, 390 + i * 6, 300 + i * 4)) for i in range(8)]
    p = FramePipeline(StubDetector())
    last = None
    for i, det in enumerate(growing):
        p.detector.dets = [det]
        last = p.process(np.zeros((480, 640, 3), np.uint8), "s", now=i * 0.2)
    car = last["detections"][0]
    assert car["approaching"] and car["moving"]
    assert car["danger"]["level"] in ("WARNING", "DANGER")
    assert "approaching" in car["message"]


@pytest.fixture
def client(tmp_path):
    app = create_app(StubDetector([PERSON_CENTER]), db_path=tmp_path / "t.db", load_model=False)
    with TestClient(app) as c:
        yield c


def test_health_ok(client):
    j = client.get("/api/health").json()
    assert j["status"] == "ok" and j["database"] is True


def test_detect_endpoint_and_history_storage(client):
    r = client.post("/api/detect?session_id=abc", content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 200
    body = r.json()
    assert body["detections"][0]["label"] == "person"
    hist = client.get("/api/history").json()["items"]
    assert len(hist) == 1 and hist[0]["label"] == "person"
    stats = client.get("/api/history/stats").json()
    assert stats["total"] == 1
    # same tracked object, same level, within the throttle window -> not logged twice
    client.post("/api/detect?session_id=abc", content=jpeg())
    assert len(client.get("/api/history").json()["items"]) == 1
    assert client.delete("/api/history").json()["deleted"] == 1
    assert client.get("/api/history").json()["items"] == []


def test_history_filter_validation(client):
    assert client.get("/api/history?level=BOGUS").status_code == 422
    assert client.get("/api/history?level=DANGER").status_code == 200


def test_bad_and_empty_image_rejected(client):
    r = client.post("/api/detect", content=b"not an image")
    assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_IMAGE"
    assert client.post("/api/detect", content=b"").status_code == 400


def test_emergency_records_event(client):
    r = client.post("/api/emergency", json={"session_id": "abc", "note": "test", "last_level": "DANGER"})
    assert r.status_code == 200 and r.json()["ok"] and "PROTOTYPE" in r.json()["notice"]
    assert len(client.get("/api/emergency").json()["items"]) == 1


def test_model_error_is_reported_not_faked(tmp_path):
    err = {"code": "MODEL_DOWNLOAD_FAILED", "message": "no internet"}
    app = create_app(StubDetector(state="error", error=err), db_path=tmp_path / "e.db", load_model=False)
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "error"
        r = c.post("/api/detect", content=jpeg())
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "MODEL_DOWNLOAD_FAILED"
        assert c.get("/api/history").json()["items"] == []     # nothing invented


def test_model_loading_returns_503(tmp_path):
    app = create_app(StubDetector(state="loading"), db_path=tmp_path / "l.db", load_model=False)
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "loading"
        assert c.post("/api/detect", content=jpeg()).status_code == 503
