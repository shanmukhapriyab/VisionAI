"""VisionGuard API (FastAPI).

POST /api/detect      body = one JPEG/PNG frame  -> detections, distance, position, danger, message
GET  /api/health      model + database status
GET  /api/history     stored detections            DELETE /api/history  clears them
GET  /api/history/stats
POST /api/emergency   records a prototype emergency event
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import config
from .database import Database, HistoryLogger
from .detector import DetectorError, YoloDetector
from .pipeline import FramePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("visionguard")
VERSION = "1.0.0"
FRONTEND_DIST = config.BASE_DIR.parent / "frontend" / "dist"


class EmergencyIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    last_level: str | None = Field(default=None, max_length=16)
    last_message: str | None = Field(default=None, max_length=300)


def create_app(detector=None, db_path: Path | None = None, load_model: bool = True) -> FastAPI:
    """App factory. `detector` may be injected in tests; in normal use the YOLO model is loaded."""
    detector = detector or YoloDetector()
    db = Database(db_path or config.DB_PATH)
    pipeline = FramePipeline(detector)
    history = HistoryLogger(db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if load_model and hasattr(detector, "start_background_load"):
            detector.start_background_load()
        yield

    app = FastAPI(title="VisionGuard API", version=VERSION, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                       allow_methods=["*"], allow_headers=["*"])
    app.state.detector, app.state.db, app.state.pipeline = detector, db, pipeline

    @app.get("/api/health")
    def health():
        m = detector.status()
        status = {"ready": "ok", "loading": "loading", "idle": "loading"}.get(m["state"], "error")
        return {"status": status, "version": VERSION, "model": m, "database": db.ok()}

    @app.post("/api/detect")
    async def detect(request: Request, session_id: str = Query(default="default", max_length=64),
                     conf: float = Query(default=config.DEFAULT_CONFIDENCE, ge=0.1, le=0.9)):
        data = await request.body()
        if not data:
            raise HTTPException(400, {"code": "EMPTY_FRAME", "message": "No image data received."})
        if len(data) > config.MAX_FRAME_BYTES:
            raise HTTPException(413, {"code": "FRAME_TOO_LARGE", "message": "Frame is too large."})
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(400, {"code": "BAD_IMAGE", "message": "Could not decode the image frame."})
        try:
            result = await run_in_threadpool(pipeline.process, img, session_id, conf)
        except DetectorError as e:
            status = 503 if e.code in ("MODEL_LOADING",) or detector.state in ("error", "loading") else 500
            raise HTTPException(status, {"code": e.code, "message": e.message})
        try:
            history.log(session_id, result["detections"], time.monotonic())
        except Exception:
            log.exception("History write failed")   # never block a safety alert because of the DB
            result["history_error"] = True
        return result

    @app.post("/api/session/reset")
    def reset_session(session_id: str = Query(default="default", max_length=64)):
        pipeline.reset_session(session_id)
        return {"ok": True}

    @app.get("/api/history")
    def get_history(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                    level: str | None = Query(None, pattern="^(SAFE|CAUTION|WARNING|DANGER)$"),
                    label: str | None = Query(None, max_length=32)):
        return {"items": db.list_history(limit, offset, level, label)}

    @app.get("/api/history/stats")
    def get_stats():
        return db.history_stats()

    @app.delete("/api/history")
    def clear_history():
        return {"deleted": db.clear_history()}

    @app.post("/api/emergency")
    def emergency(body: EmergencyIn):
        rec = db.add_emergency(body.session_id, body.note, body.last_level, body.last_message)
        return {
            "ok": True, **rec,
            "notice": ("PROTOTYPE: this button only records the event locally. It does NOT contact "
                       "anyone. In a real emergency call your local emergency number."),
        }

    @app.get("/api/emergency")
    def list_emergency():
        return {"items": db.list_emergency()}

    @app.exception_handler(HTTPException)
    async def http_exc(_, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
        return JSONResponse({"error": detail}, status_code=exc.status_code)

    if FRONTEND_DIST.exists():   # optional: serve the built UI from the same port
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")
    return app


app = create_app()
